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
import {
  search,
  searchKeymap,
  closeSearchPanel,
  highlightSelectionMatches,
  openSearchPanel,
} from "@codemirror/search";
import {
  autocompletion,
  completionKeymap,
  closeBrackets,
  closeBracketsKeymap,
  snippet,
  snippetCompletion,
} from "@codemirror/autocomplete";
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

const METADATA_COMPLETION_TEMPLATES = [
  ["@name", '@name: "#{名称}"', "测试或资源名称"],
  ["@description", '@description: "#{描述}"', "说明当前文件用途"],
  ["@tags", '@tags: [#{标签}]', "测试标签"],
  ["@author", '@author: "#{作者}"', "作者"],
  ["@date", '@date: "#{日期}"', "日期"],
  ["@import", '@import: "#{path}.resource"', "导入 Resource 文件"],
  ["@remote", '@remote: "http://#{host}:#{port}/" as #{alias}', "远程关键字服务"],
  ["@data", '@data: "#{file}.csv" using csv', "数据驱动文件"],
];

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
// Compartments for dynamic reconfiguration are now per-instance;
// buildExtensions() receives them via opts._languageCompartment
// and opts._readonlyCompartment.
// ============================================================

// ============================================================
// DSL / Resource Completions
// ============================================================

function createCompletionContext() {
  return {
    language: "plain",
    keywords: [],
    variables: [],
  };
}

function isDslLikeLanguage(language) {
  return language === "dsl" || language === "resource";
}

function dslCompletionSource(context) {
  const inst = _activeBridgeInstance;
  const completionContext = (inst && inst.completionContext) || createCompletionContext();
  if (!isDslLikeLanguage(completionContext.language)) {
    return null;
  }

  const line = context.state.doc.lineAt(context.pos);
  const prefix = line.text.slice(0, context.pos - line.from);
  const nextChar = line.text.slice(context.pos - line.from, context.pos - line.from + 1);
  const variableMatch = prefix.match(/\$\{([A-Za-z0-9_.-]*)$/);
  if (variableMatch) {
    const from = context.pos - variableMatch[1].length;
    return variableCompletions(from, completionContext.variables);
  }

  const metadataMatch = prefix.match(/^(\s*)(@[\w-]*)$/);
  if (metadataMatch) {
    return metadataCompletions(line.from + metadataMatch[1].length);
  }

  const parameterMatch = parameterCompletionMatch(prefix, context.explicit);
  if (parameterMatch) {
    return parameterCompletions(
      line.from + parameterMatch.from,
      line.from + parameterMatch.to,
      completionContext.keywords,
      parameterMatch,
    );
  }

  const keywordMatch = keywordCompletionMatch(prefix);
  if (keywordMatch) {
    return keywordCompletions(
      line.from + keywordMatch.from,
      line.from + keywordMatch.to,
      completionContext.keywords,
      {
        inBracket: keywordMatch.inBracket,
        replaceNextBracket: keywordMatch.inBracket && nextChar === "]",
      },
    );
  }

  if (!context.explicit) {
    return null;
  }

  return keywordCompletions(context.pos, context.pos, completionContext.keywords, {
    inBracket: false,
  });
}

function keywordCompletionMatch(prefix) {
  const bracketMatch = prefix.match(/\[([^\]\n]*)$/);
  if (bracketMatch) {
    const typed = bracketMatch[1];
    return {
      from: prefix.length - typed.length,
      to: prefix.length,
      inBracket: true,
    };
  }

  const bareMatch = prefix.match(/(?:^|[\s=,|])([\p{L}\p{N}_-]{1,48})$/u);
  if (!bareMatch) {
    return null;
  }

  const typed = bareMatch[1];
  return {
    from: prefix.length - typed.length,
    to: prefix.length,
    inBracket: false,
  };
}

function keywordCompletions(from, to, keywords, options = {}) {
  const uniqueKeywords = uniqueByLabel(keywords)
    .filter((keyword) => keyword.name)
    .slice(0, 500);

  if (uniqueKeywords.length === 0) {
    return null;
  }

  return {
    from,
    to,
    options: uniqueKeywords.map((keyword) => ({
        label: keyword.name,
        type: "function",
        detail: keywordDetail(keyword),
        info: keyword.documentation || keyword.source || "pytest-dsl 关键字",
        section: "关键字",
        apply: keywordCompletionApply(keywordSnippetTemplate(keyword, options), options),
      })),
    validFor: options.inBracket ? /^[^\]\n]*$/ : /^[\p{L}\p{N}_-]*$/u,
  };
}

function keywordCompletionApply(template, options = {}) {
  const applySnippet = snippet(template);
  return (view, completion, from, to) => {
    const replaceTo = options.replaceNextBracket && view.state.doc.sliceString(to, to + 1) === "]" ? to + 1 : to;
    applySnippet(view, completion, from, replaceTo);
  };
}

function keywordSnippetTemplate(keyword, options = {}) {
  const name = escapeSnippetText(keyword.name);
  const prefix = options.inBracket ? "" : "[";
  const params = (keyword.parameters || [])
    .map((param) => param.name || param.mapping)
    .filter(Boolean)
    .slice(0, 8);
  const paramText = params.length > 0
    ? `, ${params.map((param) => `${escapeSnippetText(param)}: #{}`).join(", ")}`
    : "";
  return `${prefix}${name}]${paramText}`;
}

function parameterCompletionMatch(prefix, explicit) {
  const call = lastClosedKeywordCall(prefix);
  if (!call) {
    return null;
  }

  const tail = prefix.slice(call.closeIndex + 1);
  const hasParameterSeparator = /^\s*,/.test(tail);
  if (!hasParameterSeparator && !explicit) {
    return null;
  }

  const lastComma = tail.lastIndexOf(",");
  const segmentStart = lastComma >= 0 ? lastComma + 1 : 0;
  const segment = tail.slice(segmentStart);
  const tokenMatch = segment.match(/^(\s*)([\p{L}\p{N}_-]*)$/u);
  if (!tokenMatch) {
    return null;
  }

  const from = call.closeIndex + 1 + segmentStart + tokenMatch[1].length;
  return {
    keywordName: call.keywordName,
    from,
    to: prefix.length,
    usedParameterNames: usedParameterNames(tail),
  };
}

function lastClosedKeywordCall(prefix) {
  const closeIndex = prefix.lastIndexOf("]");
  if (closeIndex < 0) {
    return null;
  }
  const openIndex = prefix.lastIndexOf("[", closeIndex);
  if (openIndex < 0) {
    return null;
  }

  const keywordName = prefix.slice(openIndex + 1, closeIndex).trim();
  if (!keywordName) {
    return null;
  }

  return {
    keywordName,
    closeIndex,
  };
}

function parameterCompletions(from, to, keywords, match) {
  const parameters = keywordParametersForName(match.keywordName, keywords)
    .filter((param) => !match.usedParameterNames.has(param.name))
    .slice(0, 80);

  if (parameters.length === 0) {
    return null;
  }

  return {
    from,
    to,
    options: parameters.map((param) =>
      snippetCompletion(`${escapeSnippetText(param.name)}: #{}`, {
        label: param.name,
        type: "property",
        detail: param.description || "关键字参数",
        info: param.default === undefined ? "" : `默认值: ${param.default}`,
        section: "参数",
      }),
    ),
    validFor: /^[\p{L}\p{N}_-]*$/u,
  };
}

function keywordParametersForName(keywordName, keywords) {
  const keyword = uniqueByLabel(keywords)
    .find((item) => item.name === keywordName);
  return normalizeKeywordParameters(keyword && keyword.parameters);
}

function normalizeKeywordParameters(parameters) {
  const seen = new Set();
  return (Array.isArray(parameters) ? parameters : [])
    .map((param) => ({
      name: String(param && (param.name || param.mapping) ? (param.name || param.mapping) : "").trim(),
      description: String(param && param.description ? param.description : ""),
      default: param ? param.default : undefined,
    }))
    .filter((param) => {
      if (!param.name || seen.has(param.name)) {
        return false;
      }
      seen.add(param.name);
      return true;
    });
}

function usedParameterNames(text) {
  const names = new Set();
  const pattern = /([\p{L}\p{N}_-]+)\s*:/gu;
  let match;
  while ((match = pattern.exec(text)) !== null) {
    names.add(match[1]);
  }
  return names;
}

function keywordDetail(keyword) {
  const params = (keyword.parameters || [])
    .map((param) => param.name || param.mapping)
    .filter(Boolean);
  if (params.length > 0) {
    return params.join(", ");
  }
  return keyword.source || keyword.categoryName || "无参数";
}

function metadataCompletions(from) {
  return {
    from,
    options: METADATA_COMPLETION_TEMPLATES.map(([label, template, detail]) =>
      snippetCompletion(template, {
        label,
        type: "property",
        detail,
        section: "元信息",
      }),
    ),
    validFor: /^@[\w-]*$/,
  };
}

function variableCompletions(from, variables) {
  const byName = new Map();
  variables
    .map((variable) => normalizeVariableCompletion(variable))
    .filter(Boolean)
    .forEach((variable) => {
      if (!byName.has(variable.name)) {
        byName.set(variable.name, variable);
      }
    });

  const options = Array.from(byName.values())
    .slice(0, 300)
    .map((variable) => ({
      label: variable.name,
      type: "variable",
      detail: variable.sourceLabel || "配置变量",
      info: variable.valuePreview ? `当前值: ${variable.valuePreview}` : undefined,
      apply: `${variable.name}}`,
      section: "变量",
    }));

  if (options.length === 0) {
    return null;
  }

  return {
    from,
    options,
    validFor: /^[A-Za-z0-9_.-]*$/,
  };
}

function normalizeVariableCompletion(variable) {
  if (typeof variable === "string") {
    return { name: variable };
  }
  if (!variable || typeof variable !== "object") {
    return null;
  }
  const name = String(variable.name || variable.path || "").trim();
  if (!name) {
    return null;
  }
  return {
    ...variable,
    name,
    sourceLabel: variable.sourceLabel || (
      variable.relativePath && variable.line
        ? `${variable.relativePath}:${variable.line}`
        : ""
    ),
    valuePreview: variable.valuePreview ? String(variable.valuePreview) : "",
  };
}

function uniqueByLabel(keywords) {
  const seen = new Set();
  const result = [];
  (Array.isArray(keywords) ? keywords : []).forEach((keyword) => {
    const name = String(keyword && keyword.name ? keyword.name : "").trim();
    if (!name || seen.has(name)) {
      return;
    }
    seen.add(name);
    result.push({
      ...keyword,
      name,
      parameters: Array.isArray(keyword.parameters) ? keyword.parameters : [],
    });
  });
  return result;
}

function uniqueStrings(values) {
  const seen = new Set();
  return (Array.isArray(values) ? values : [])
    .map((value) => String(value || "").trim())
    .filter((value) => {
      if (!value || seen.has(value)) {
        return false;
      }
      seen.add(value);
      return true;
    })
    .sort((left, right) => left.localeCompare(right, "zh-CN"));
}

function escapeSnippetText(value) {
  return String(value || "").replace(/[\\{}]/g, "\\$&");
}

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
    (opts._languageCompartment || new Compartment()).of(StreamLanguage.define({ token: (s) => { s.next(); return null; } })),
    syntaxHighlighting(highlight),

    // Features
    foldGutter(),
    search(),
    highlightSelectionMatches(),
    autocompletion({ override: [dslCompletionSource], activateOnTyping: true }),
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
    (opts._readonlyCompartment || new Compartment()).of([]),

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
        const variableName = variableAtMouseEvent(view, event);
        if (variableName && opts.onDefinitionRequest) {
          event.preventDefault();
          opts.onDefinitionRequest({
            variableName,
            source: "Mod-Click",
            showAll: event.altKey,
          });
          return true;
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
        const variableName = variableAtSelection(view);
        if (variableName && opts.onDefinitionRequest) {
          event.preventDefault();
          opts.onDefinitionRequest({
            variableName,
            source: "F12",
            showAll: event.altKey,
          });
          return true;
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

function variableAtMouseEvent(view, event) {
  const pos = view.posAtCoords({ x: event.clientX, y: event.clientY });
  if (pos == null) return null;
  return variableAtPosition(view.state, pos);
}

function keywordAtSelection(view) {
  return keywordAtPosition(view.state, view.state.selection.main.head);
}

function variableAtSelection(view) {
  return variableAtPosition(view.state, view.state.selection.main.head);
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

function variableAtPosition(state, pos) {
  const line = state.doc.lineAt(pos);
  const offset = pos - line.from;
  const pattern = /\$\{([A-Za-z0-9_.-]+)\}/g;
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
// Bridge — the public API object (multi-instance)
// ============================================================

// Track which instance is active so the completion source can
// resolve the right per-instance context.
let _activeBridgeInstance = null;

const bridge = {
  _instances: Object.create(null),
  _activeKey: null,
  _nextId: 0,

  _activeInstance() {
    return this._activeKey ? this._instances[this._activeKey] || null : null;
  },

  create(key, parent, opts = {}) {
    const resolvedKey = key || `cm-${++this._nextId}`;
    if (this._instances[resolvedKey]) {
      this.destroy(resolvedKey);
    }

    const langComp = new Compartment();
    const roComp = new Compartment();

    // Build per-instance extensions with its own compartments.
    const extensions = buildExtensions({
      ...opts,
      _languageCompartment: langComp,
      _readonlyCompartment: roComp,
    });

    const state = EditorState.create({
      doc: "",
      extensions,
    });

    const container = document.createElement("div");
    container.className = "cm-instance";
    container.style.display = "none";
    container.dataset.key = resolvedKey;
    parent.appendChild(container);

    const view = new EditorView({
      state,
      parent: container,
    });

    this._instances[resolvedKey] = {
      view,
      dom: container,
      opts,
      extensions,
      completionContext: createCompletionContext(),
      languageCompartment: langComp,
      readonlyCompartment: roComp,
    };

    return resolvedKey;
  },

  createEditor(parent, opts = {}) {
    const key = this.create("main", parent, opts);
    this.show(key);
    return this._instances[key] ? this._instances[key].view : null;
  },

  show(key) {
    if (!key || !this._instances[key]) return;
    // Save current scroll/selection on outgoing instance
    if (this._activeKey && this._activeKey !== key) {
      const cur = this._instances[this._activeKey];
      if (cur && cur.view) {
        try {
          const scroll = cur.view.scrollSnapshot();
          cur._scrollSnapshot = scroll;
          cur._selection = cur.view.state.selection.main;
        } catch (_) {
          // ignore
        }
      }
    }
    // Hide all instances
    for (const k of Object.keys(this._instances)) {
      const inst = this._instances[k];
      if (inst && inst.dom) {
        inst.dom.style.display = k === key ? "" : "none";
      }
    }
    this._activeKey = key;
    _activeBridgeInstance = this._instances[key] || null;

    // Restore scroll/selection on incoming instance
    const inst = this._instances[key];
    if (inst && inst.view) {
      if (inst._scrollSnapshot) {
        try {
          inst.view.requestMeasure({
            read() { return inst._scrollSnapshot; },
            write(snap) {
              if (snap) inst.view.scrollSnapshot(snap);
            },
          });
        } catch (_) {
          // ignore
        }
      }
      if (inst._selection) {
        try {
          inst.view.dispatch({ selection: inst._selection, scrollIntoView: false });
        } catch (_) {
          // ignore
        }
      }
      // Focus if not readonly
      if (inst.view.contentDOM.contentEditable !== "false") {
        inst.view.focus();
      }
    }
  },

  destroy(key) {
    const inst = this._instances[key];
    if (!inst) return;
    if (inst.view) {
      try { inst.view.destroy(); } catch (_) { /* ignore */ }
    }
    if (inst.dom && inst.dom.parentElement) {
      inst.dom.parentElement.removeChild(inst.dom);
    }
    delete this._instances[key];
    if (this._activeKey === key) {
      this._activeKey = null;
      _activeBridgeInstance = null;
      // Try to find another instance to activate
      const keys = Object.keys(this._instances);
      if (keys.length > 0) {
        this.show(keys[0]);
      }
    }
  },

  getActiveKey() {
    return this._activeKey;
  },

  count() {
    return Object.keys(this._instances).length;
  },

  destroyAll() {
    const keys = Object.keys(this._instances);
    for (const key of keys) {
      this.destroy(key);
    }
  },

  setLanguage(lang) {
    const inst = this._activeInstance();
    if (!inst) return;
    inst.completionContext = {
      ...inst.completionContext,
      language: lang || "plain",
    };
    const language = LANGUAGES[lang];
    if (language) {
      inst.view.dispatch({
        effects: inst.languageCompartment.reconfigure(language),
      });
    }
  },

  setCompletionContext(context = {}) {
    const inst = this._activeInstance();
    if (!inst) return;
    inst.completionContext = {
      language: context.language || inst.completionContext.language || "plain",
      keywords: Array.isArray(context.keywords) ? context.keywords : [],
      variables: Array.isArray(context.variables) ? context.variables : [],
    };
  },

  setContent(text) {
    const inst = this._activeInstance();
    if (!inst) return;
    const { state } = inst.view;
    inst.view.dispatch({
      changes: { from: 0, to: state.doc.length, insert: text },
      selection: { anchor: 0 },
      effects: [
        setDebugStateEffect.of({ debugStartLine: null, currentDebugLine: null, debugSelection: null }),
        EditorView.scrollIntoView(0, { y: "start" }),
      ],
    });
  },

  getContent() {
    const inst = this._activeInstance();
    if (!inst) return "";
    return inst.view.state.doc.toString();
  },

  lineCount() {
    const inst = this._activeInstance();
    if (!inst) return 0;
    return inst.view.state.doc.lines;
  },

  getSelection() {
    const inst = this._activeInstance();
    if (!inst) return null;
    const { state } = inst.view;
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
    const inst = this._activeInstance();
    if (!inst) return null;
    return keywordAtSelection(inst.view);
  },

  insertText(text) {
    const inst = this._activeInstance();
    if (!inst) return;
    const { state } = inst.view;
    const range = state.selection.main;
    const insert = String(text || "");
    inst.view.dispatch({
      changes: { from: range.from, to: range.to, insert },
      selection: { anchor: range.from + insert.length },
      scrollIntoView: true,
    });
    inst.view.focus();
  },

  setEnabled(enabled) {
    const inst = this._activeInstance();
    if (!inst) return;
    inst.view.dispatch({
      effects: inst.readonlyCompartment.reconfigure(
        enabled ? [] : [EditorState.readOnly.of(true)],
      ),
    });
    inst.view.contentDOM.contentEditable = String(enabled);
  },

  setDebugState(debugState) {
    const inst = this._activeInstance();
    if (!inst) return;
    inst.view.dispatch({
      effects: setDebugStateEffect.of({
        debugStartLine: debugState.debugStartLine || null,
        currentDebugLine: debugState.currentDebugLine || null,
        debugSelection: debugState.debugSelection || null,
      }),
    });
  },

  scrollToLine(lineNumber) {
    const inst = this._activeInstance();
    if (!inst) return;
    const { doc } = inst.view.state;
    if (lineNumber < 1 || lineNumber > doc.lines) return;
    const line = doc.line(lineNumber);
    inst.view.dispatch({
      effects: EditorView.scrollIntoView(line.from, { y: "center" }),
    });
  },

  goToLine(lineNumber, columnNumber = 1) {
    const inst = this._activeInstance();
    if (!inst) return;
    const { doc } = inst.view.state;
    if (lineNumber < 1 || lineNumber > doc.lines) return;
    const line = doc.line(lineNumber);
    const column = Math.max(1, Math.trunc(Number(columnNumber)) || 1);
    const target = Math.min(line.to, line.from + column - 1);
    inst.view.dispatch({
      selection: { anchor: target },
      effects: EditorView.scrollIntoView(target, { y: "center" }),
    });
    inst.view.focus();
  },

  closeSearch() {
    const inst = this._activeInstance();
    if (inst && inst.view) closeSearchPanel(inst.view);
  },

  openSearch(replace = false) {
    const inst = this._activeInstance();
    if (!inst || !inst.view) return;
    openSearchPanel(inst.view);
    if (replace) {
      setTimeout(() => {
        const replaceInput = inst.view.dom.querySelector(".cm-panel.cm-search input[name='replace']");
        if (replaceInput) {
          replaceInput.focus();
          replaceInput.select();
        }
      }, 0);
    }
  },

  focus() {
    const inst = this._activeInstance();
    if (inst && inst.view) inst.view.focus();
  },

  _completionContext: createCompletionContext(),
};

// Named exports → CM6.createEditor(), CM6.setContent(), etc.
// Standard API (backward-compatible)
export const createEditor = bridge.createEditor.bind(bridge);
export const setLanguage = bridge.setLanguage.bind(bridge);
export const setCompletionContext = bridge.setCompletionContext.bind(bridge);
export const setContent = bridge.setContent.bind(bridge);
export const getContent = bridge.getContent.bind(bridge);
export const lineCount = bridge.lineCount.bind(bridge);
export const getSelection = bridge.getSelection.bind(bridge);
export const getKeywordUnderCursor = bridge.getKeywordUnderCursor.bind(bridge);
export const insertText = bridge.insertText.bind(bridge);
export const setEnabled = bridge.setEnabled.bind(bridge);
export const setDebugState = bridge.setDebugState.bind(bridge);
export const scrollToLine = bridge.scrollToLine.bind(bridge);
export const goToLine = bridge.goToLine.bind(bridge);
export const closeSearch = bridge.closeSearch.bind(bridge);
export const openSearch = bridge.openSearch.bind(bridge);
export const focus = bridge.focus.bind(bridge);
export const destroy = bridge.destroy.bind(bridge);

// Multi-instance API (new)
export const create = bridge.create.bind(bridge);
export const show = bridge.show.bind(bridge);
export const destroyKey = bridge.destroy.bind(bridge);
export const getActiveKey = bridge.getActiveKey.bind(bridge);
export const count = bridge.count.bind(bridge);
export const destroyAll = bridge.destroyAll.bind(bridge);
