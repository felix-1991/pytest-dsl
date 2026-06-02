/**
 * CodeMirror 6 bridge — exposes a clean API as window.CM6
 * for the renderer.js to use without knowing CM6 internals.
 */

import { EditorState, Compartment, StateEffect, StateField } from "@codemirror/state";
import {
  EditorView,
  keymap,
  lineNumbers,
  highlightActiveLineGutter,
  highlightActiveLine,
  drawSelection,
  highlightSpecialChars,
  gutter,
  GutterMarker,
  Decoration,
  placeholder as cmPlaceholder,
} from "@codemirror/view";
import {
  defaultKeymap,
  history,
  historyKeymap,
  indentWithTab,
} from "@codemirror/commands";
import {
  StreamLanguage,
  foldGutter,
  foldKeymap,
  indentOnInput,
  bracketMatching,
  syntaxHighlighting,
} from "@codemirror/language";
import { search, searchKeymap, closeSearchPanel, highlightSelectionMatches } from "@codemirror/search";
import { autocompletion, completionKeymap, closeBrackets, closeBracketsKeymap } from "@codemirror/autocomplete";
import { tagHighlighter, tags } from "@lezer/highlight";
import { showMinimap } from "@replit/codemirror-minimap";

// ============================================================
// Language Definitions (StreamLanguage — ported from old regex)
// ============================================================

const dslLanguage = StreamLanguage.define({
  name: "dsl",
  token(stream) {
    if (stream.sol() && stream.eatSpace() && stream.eat("#")) {
      stream.skipToEnd();
      return "comment";
    }
    if (stream.match(/^#[^\n]*/)) return "comment";
    if (stream.match(/^@[a-zA-Z_][\w-]*/)) return "meta";
    if (stream.match(/^\$\{[^}]+\}/)) return "variableName";
    if (stream.match(/^\[[^\]]+\]/)) return "keyword";
    if (stream.match(/^"[^"]*"/)) return "string";
    if (stream.match(/^'[^']*'/)) return "string";
    stream.next();
    return null;
  },
});

const yamlLanguage = StreamLanguage.define({
  name: "yaml",
  token(stream) {
    if (stream.sol() && stream.eatSpace() && stream.eat("#")) {
      stream.skipToEnd();
      return "comment";
    }
    if (stream.match(/^#[^\n]*/)) return "comment";
    if (stream.sol() && stream.match(/^[\w][-.\w]*(?=\s*:)/)) return "propertyName";
    if (stream.match(/^"[^"]*"/)) return "string";
    if (stream.match(/^'[^']*'/)) return "string";
    if (stream.match(/\b(?:true|false|null)\b/)) return "bool";
    if (stream.match(/\b\d+(?:\.\d+)?\b/)) return "number";
    stream.next();
    return null;
  },
});

const PYTHON_KEYWORDS = new Set([
  "class", "def", "return", "if", "elif", "else", "for", "while",
  "try", "except", "finally", "with", "as", "import", "from",
  "pass", "raise", "True", "False", "None",
]);

const pythonLanguage = StreamLanguage.define({
  name: "python",
  token(stream) {
    if (stream.sol() && stream.eatSpace() && stream.eat("#")) {
      stream.skipToEnd();
      return "comment";
    }
    if (stream.match(/^#[^\n]*/)) return "comment";
    if (stream.sol() && stream.match(/^@\w[\w.]*/)) return "meta";
    if (stream.match(/^[a-zA-Z_]\w*/)) {
      const word = stream.current();
      return PYTHON_KEYWORDS.has(word) ? "keyword" : null;
    }
    if (stream.match(/^"[^"]*"/)) return "string";
    if (stream.match(/^'[^']*'/)) return "string";
    stream.next();
    return null;
  },
});

const markdownLanguage = StreamLanguage.define({
  name: "markdown",
  token(stream) {
    if (stream.sol() && stream.match(/^\s{0,3}(?:```|~~~)/)) {
      stream.skipToEnd();
      return "monospace";
    }
    if (stream.sol() && stream.match(/^\s{0,3}#{1,6}\s+/)) {
      stream.skipToEnd();
      return "heading";
    }
    if (stream.sol() && stream.match(/^\s{0,3}>/)) {
      stream.skipToEnd();
      return "quote";
    }
    if (stream.sol() && stream.match(/^\s*([-*+]|\d+\.)\s/)) return "list";
    if (stream.match(/^`[^`]+`/)) return "monospace";
    if (stream.match(/^\*\*[^*]+\*\*/)) return "strong";
    if (stream.match(/^\[[^\]]+\]\([^)]+\)/)) return "link";
    stream.next();
    return null;
  },
});

const LANGUAGES = {
  dsl: dslLanguage,
  resource: dslLanguage,
  yaml: yamlLanguage,
  python: pythonLanguage,
  markdown: markdownLanguage,
};

// ============================================================
// Syntax Highlighting (map Lezer tags → our .tok-* CSS classes)
// ============================================================

const highlight = tagHighlighter([
  { tag: tags.meta, class: "tok-meta" },
  { tag: tags.variableName, class: "tok-var" },
  { tag: tags.keyword, class: "tok-keyword" },
  { tag: tags.string, class: "tok-str" },
  { tag: tags.comment, class: "tok-comment" },
  { tag: tags.number, class: "tok-number" },
  { tag: tags.bool, class: "tok-number" },
  { tag: tags.propertyName, class: "tok-key" },
  { tag: tags.heading, class: "tok-heading" },
  { tag: tags.quote, class: "tok-quote" },
  { tag: tags.list, class: "tok-list" },
  { tag: tags.monospace, class: "tok-code" },
  { tag: tags.strong, class: "tok-strong" },
  { tag: tags.link, class: "tok-link" },
]);

// ============================================================
// Debug State — shared state, line decorations, gutter markers
// ============================================================

const setDebugStateEffect = StateEffect.define();

const debugStateField = StateField.define({
  create() {
    return { debugStartLine: null, currentDebugLine: null, debugSelection: null };
  },
  update(value, tr) {
    for (const effect of tr.effects) {
      if (effect.is(setDebugStateEffect)) return effect.value;
    }
    return value;
  },
});

const debugLineDecorations = StateField.define({
  create() {
    return Decoration.none;
  },
  update(_value, tr) {
    const ds = tr.state.field(debugStateField);
    const doc = tr.state.doc;
    const builder = [];

    if (ds.debugSelection) {
      const from = Math.max(1, ds.debugSelection.startLine);
      const to = Math.min(doc.lines, ds.debugSelection.endLine);
      for (let i = from; i <= to; i++) {
        builder.push(Decoration.line({ class: "is-debug-selected" }).range(doc.line(i).from));
      }
    }
    if (ds.debugStartLine && ds.debugStartLine >= 1 && ds.debugStartLine <= doc.lines) {
      builder.push(Decoration.line({ class: "is-debug-start" }).range(doc.line(ds.debugStartLine).from));
    }
    if (ds.currentDebugLine && ds.currentDebugLine >= 1 && ds.currentDebugLine <= doc.lines) {
      builder.push(Decoration.line({ class: "is-debug-current" }).range(doc.line(ds.currentDebugLine).from));
    }

    builder.sort((a, b) => a.from - b.from);
    return Decoration.set(builder);
  },
  provide: (f) => EditorView.decorations.from(f),
});

/** Gutter marker dot for debug start breakpoint. */
class DebugStartMarker extends GutterMarker {
  toDOM() {
    const dot = document.createElement("div");
    dot.className = "cm-debug-dot";
    return dot;
  }
}

const debugGutterMarkers = StateField.define({
  create() {
    return [];
  },
  update(_value, tr) {
    const ds = tr.state.field(debugStateField);
    const doc = tr.state.doc;
    const markers = [];
    if (ds.debugStartLine && ds.debugStartLine >= 1 && ds.debugStartLine <= doc.lines) {
      markers.push({ line: ds.debugStartLine, marker: new DebugStartMarker() });
    }
    return markers;
  },
});

const debugGutterExt = gutter({
  class: "cm-debug-gutter",
  lineMarker(view, line) {
    const markers = view.state.field(debugGutterMarkers);
    const lineNum = view.state.doc.lineAt(line.from).number;
    const found = markers.find((m) => m.line === lineNum);
    return found ? found.marker : null;
  },
  lineMarkerChange(update) {
    for (const tr of update.transactions) {
      for (const effect of tr.effects) {
        if (effect.is(setDebugStateEffect)) return true;
      }
    }
    return false;
  },
  domEventHandlers: {
    mousedown(view, line, event) {
      if (event.target && event.target.closest(".cm-debug-gutter")) {
        const lineNum = view.state.doc.lineAt(line.from).number;
        if (bridge._opts.onGutterClick) {
          bridge._opts.onGutterClick(lineNum);
        }
        return true;
      }
      return false;
    },
  },
  initialSpacer: () => new DebugStartMarker(),
});

// ============================================================
// Compartments (for dynamic reconfiguration)
// ============================================================

const languageCompartment = new Compartment();
const readonlyCompartment = new Compartment();

// ============================================================
// Theme
// ============================================================

const darkTheme = EditorView.theme({
  "&": {
    backgroundColor: "#0f172a",
    color: "#e5edf7",
    fontSize: "13px",
    height: "100%",
  },
  ".cm-content": {
    fontFamily: "var(--mono)",
    lineHeight: "22px",
    caretColor: "#e5edf7",
    tabSize: "4",
    padding: "14px 0",
  },
  ".cm-gutters": {
    backgroundColor: "#0f172a",
    color: "#64748b",
    border: "none",
  },
  ".cm-activeLineGutter": {
    backgroundColor: "rgba(96, 165, 250, 0.08)",
    color: "#94a3b8",
  },
  ".cm-activeLine": {
    backgroundColor: "rgba(96, 165, 250, 0.08)",
  },
  ".cm-selectionBackground": {
    backgroundColor: "rgba(96, 165, 250, 0.32) !important",
  },
  "&.cm-focused .cm-selectionBackground": {
    backgroundColor: "rgba(96, 165, 250, 0.32) !important",
  },
  ".cm-cursor": {
    borderLeftColor: "#e5edf7",
  },
  ".cm-searchMatch": {
    backgroundColor: "rgba(251, 191, 36, 0.3)",
    borderRadius: "2px",
    outline: "none",
  },
  ".cm-searchMatch.cm-searchMatch-selected": {
    backgroundColor: "rgba(251, 191, 36, 0.5)",
  },
  ".cm-panels": {
    backgroundColor: "#1e293b",
    color: "#e5edf7",
    borderBottom: "1px solid rgba(148, 163, 184, 0.25)",
  },
  ".cm-panels.cm-panels-top": {
    borderBottom: "1px solid rgba(148, 163, 184, 0.25)",
  },
  ".cm-textfield": {
    backgroundColor: "#0f172a",
    color: "#e5edf7",
    border: "1px solid rgba(148, 163, 184, 0.3)",
    borderRadius: "4px",
    fontSize: "12px",
  },
  ".cm-button": {
    backgroundColor: "rgba(148, 163, 184, 0.18)",
    color: "#e5edf7",
    border: "none",
    borderRadius: "4px",
    fontSize: "12px",
    backgroundImage: "none",
  },
  ".cm-button:hover": {
    backgroundColor: "rgba(148, 163, 184, 0.3)",
  },
  ".cm-panel.cm-search label": {
    color: "#94a3b8",
    fontSize: "12px",
  },
  ".cm-foldPlaceholder": {
    backgroundColor: "rgba(148, 163, 184, 0.15)",
    color: "#94a3b8",
    border: "none",
    borderRadius: "3px",
    padding: "0 4px",
  },
  ".cm-tooltip": {
    backgroundColor: "#1e293b",
    color: "#e5edf7",
    border: "1px solid rgba(148, 163, 184, 0.25)",
    borderRadius: "6px",
  },
  ".cm-tooltip-autocomplete > ul > li[aria-selected]": {
    backgroundColor: "rgba(96, 165, 250, 0.2)",
  },
  ".cm-minimap": {
    backgroundColor: "#0f172a",
  },
  ".cm-minimap .cm-minimap-overlay": {
    backgroundColor: "rgba(96, 165, 250, 0.15)",
  },
  ".cm-scroller::-webkit-scrollbar": {
    width: "8px",
    height: "8px",
  },
  ".cm-scroller::-webkit-scrollbar-track": {
    backgroundColor: "transparent",
  },
  ".cm-scroller::-webkit-scrollbar-thumb": {
    backgroundColor: "rgba(148, 163, 184, 0.25)",
    borderRadius: "4px",
  },
  ".cm-scroller::-webkit-scrollbar-thumb:hover": {
    backgroundColor: "rgba(148, 163, 184, 0.4)",
  },
});

// ============================================================
// Build extensions factory (stored for setContent re-use)
// ============================================================

function buildExtensions(opts) {
  return [
    // History (undo/redo)
    history(),
    keymap.of([
      ...defaultKeymap,
      ...historyKeymap,
      ...searchKeymap,
      ...foldKeymap,
      ...completionKeymap,
      ...closeBracketsKeymap,
      indentWithTab,
    ]),

    // Visual
    drawSelection(),
    highlightActiveLine(),
    highlightActiveLineGutter(),
    highlightSpecialChars(),
    bracketMatching(),
    closeBrackets(),
    indentOnInput(),

    // Language (compartment for dynamic switching)
    languageCompartment.of(StreamLanguage.define({ token: (s) => { s.next(); return null; } })),
    syntaxHighlighting(highlight),

    // Features
    foldGutter(),
    search(),
    highlightSelectionMatches(),
    autocompletion(),
    // Minimap (Facet-based API for @replit/codemirror-minimap >= 0.5)
    showMinimap.of({
      create() {
        const dom = document.createElement("div");
        return { dom };
      },
      displayText: "characters",
      showOverlay: "always",
    }),

    // Gutters: debug markers → line numbers
    debugGutterExt,
    lineNumbers(),

    // Debug decoration fields
    debugStateField,
    debugLineDecorations,
    debugGutterMarkers,

    // Read-only compartment
    readonlyCompartment.of([]),

    // Update listener
    EditorView.updateListener.of((update) => {
      if (update.docChanged && opts.onContentChange) {
        opts.onContentChange();
      }
      if (update.selectionSet && opts.onSelectionChange) {
        opts.onSelectionChange();
      }
    }),

    // Placeholder text
    cmPlaceholder("从左侧打开文件"),

    EditorView.domEventHandlers({
      mousedown(event, view) {
        if (event.button !== 0 || !(event.metaKey || event.ctrlKey)) {
          return false;
        }
        const keywordName = keywordAtMouseEvent(view, event);
        if (!keywordName || !opts.onDefinitionRequest) {
          return false;
        }
        event.preventDefault();
        opts.onDefinitionRequest({
          keywordName,
          source: "Mod-Click",
          showAll: event.altKey,
        });
        return true;
      },
      keydown(event, view) {
        if (event.key !== "F12") {
          return false;
        }
        const keywordName = keywordAtSelection(view);
        if (!keywordName || !opts.onDefinitionRequest) {
          return false;
        }
        event.preventDefault();
        opts.onDefinitionRequest({
          keywordName,
          source: "F12",
          showAll: event.altKey,
        });
        return true;
      },
    }),

    // Theme
    darkTheme,
  ];
}

function keywordAtMouseEvent(view, event) {
  const pos = view.posAtCoords({ x: event.clientX, y: event.clientY });
  if (pos == null) return null;
  return keywordAtPosition(view.state, pos);
}

function keywordAtSelection(view) {
  return keywordAtPosition(view.state, view.state.selection.main.head);
}

function keywordAtPosition(state, pos) {
  const line = state.doc.lineAt(pos);
  const offset = pos - line.from;
  const pattern = /\[([^\]]+)\]/g;
  let match;
  while ((match = pattern.exec(line.text)) !== null) {
    const start = match.index;
    const end = start + match[0].length;
    if (offset >= start && offset <= end) {
      return match[1].trim() || null;
    }
  }
  return null;
}

// ============================================================
// Bridge — the public API object
// ============================================================

const bridge = {
  _view: null,
  _opts: {},
  _extensions: null,

  createEditor(parent, opts = {}) {
    if (this._view) {
      this._view.destroy();
    }
    this._opts = opts;
    this._extensions = buildExtensions(opts);

    const state = EditorState.create({
      doc: "",
      extensions: this._extensions,
    });

    this._view = new EditorView({
      state,
      parent,
    });

    return this._view;
  },

  setLanguage(lang) {
    if (!this._view) return;
    const language = LANGUAGES[lang];
    if (language) {
      this._view.dispatch({
        effects: languageCompartment.reconfigure(language),
      });
    }
  },

  setContent(text) {
    if (!this._view) return;
    const { state } = this._view;
    // Replace entire document content via transaction (preserves extensions)
    this._view.dispatch({
      changes: { from: 0, to: state.doc.length, insert: text },
      selection: { anchor: 0 },
      effects: [
        setDebugStateEffect.of({ debugStartLine: null, currentDebugLine: null, debugSelection: null }),
        EditorView.scrollIntoView(0, { y: "start" }),
      ],
    });
  },

  getContent() {
    if (!this._view) return "";
    return this._view.state.doc.toString();
  },

  lineCount() {
    if (!this._view) return 0;
    return this._view.state.doc.lines;
  },

  getSelection() {
    if (!this._view) return null;
    const { state } = this._view;
    const range = state.selection.main;
    if (range.empty) return null;

    const fromLine = state.doc.lineAt(range.from).number;
    const toLine = state.doc.lineAt(range.to).number;
    const fromPos = state.doc.line(fromLine).from;
    const toPos = state.doc.line(toLine).to;
    const content = state.doc.sliceString(fromPos, toPos);
    if (!content.trim()) return null;

    return { startLine: fromLine, endLine: toLine, content };
  },

  getKeywordUnderCursor() {
    if (!this._view) return null;
    return keywordAtSelection(this._view);
  },

  insertText(text) {
    if (!this._view) return;
    const { state } = this._view;
    const range = state.selection.main;
    const insert = String(text || "");
    this._view.dispatch({
      changes: { from: range.from, to: range.to, insert },
      selection: { anchor: range.from + insert.length },
      scrollIntoView: true,
    });
    this._view.focus();
  },

  setEnabled(enabled) {
    if (!this._view) return;
    this._view.dispatch({
      effects: readonlyCompartment.reconfigure(
        enabled ? [] : [EditorState.readOnly.of(true)],
      ),
    });
    this._view.contentDOM.contentEditable = String(enabled);
  },

  setDebugState(debugState) {
    if (!this._view) return;
    this._view.dispatch({
      effects: setDebugStateEffect.of({
        debugStartLine: debugState.debugStartLine || null,
        currentDebugLine: debugState.currentDebugLine || null,
        debugSelection: debugState.debugSelection || null,
      }),
    });
  },

  scrollToLine(lineNumber) {
    if (!this._view) return;
    const { doc } = this._view.state;
    if (lineNumber < 1 || lineNumber > doc.lines) return;
    const line = doc.line(lineNumber);
    this._view.dispatch({
      effects: EditorView.scrollIntoView(line.from, { y: "center" }),
    });
  },

  closeSearch() {
    if (this._view) closeSearchPanel(this._view);
  },

  focus() {
    if (this._view) this._view.focus();
  },

  destroy() {
    if (this._view) {
      this._view.destroy();
      this._view = null;
    }
  },
};

// Named exports → CM6.createEditor(), CM6.setContent(), etc.
export const createEditor = bridge.createEditor.bind(bridge);
export const setLanguage = bridge.setLanguage.bind(bridge);
export const setContent = bridge.setContent.bind(bridge);
export const getContent = bridge.getContent.bind(bridge);
export const lineCount = bridge.lineCount.bind(bridge);
export const getSelection = bridge.getSelection.bind(bridge);
export const getKeywordUnderCursor = bridge.getKeywordUnderCursor.bind(bridge);
export const insertText = bridge.insertText.bind(bridge);
export const setEnabled = bridge.setEnabled.bind(bridge);
export const setDebugState = bridge.setDebugState.bind(bridge);
export const scrollToLine = bridge.scrollToLine.bind(bridge);
export const closeSearch = bridge.closeSearch.bind(bridge);
export const focus = bridge.focus.bind(bridge);
export const destroy = bridge.destroy.bind(bridge);
