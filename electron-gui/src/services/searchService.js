const fs = require("node:fs");
const { spawnSync } = require("node:child_process");
const crypto = require("node:crypto");

const {
  listEditableFiles,
  resolveProjectFile,
} = require("./projectService");

const DEFAULT_MAX_MATCHES = 1000;
const DEFAULT_MAX_FILE_SIZE_BYTES = 2 * 1024 * 1024;
const DEFAULT_BATCH_SIZE = 25;
const GIT_CHECK_IGNORE_CHUNK_SIZE = 1000;
const GIT_CHECK_IGNORE_MAX_BUFFER = 16 * 1024 * 1024;
const MAX_MATCH_PREVIEW_CHARS = 240;
const MATCH_PREVIEW_CONTEXT_CHARS = 96;
const MAX_MATCH_TEXT_CHARS = 1024;

function searchProject(projectRoot, request = {}) {
  const query = normalizeQuery(request.query);
  const options = normalizeSearchOptions(request.options);
  const matcher = createMatcher(query, options);
  const result = emptySearchResult(query, options);

  for (const file of searchCandidates(projectRoot, request)) {
    const scan = scanSearchFile(projectRoot, file, matcher, options, result);
    appendScanResult(result, scan);
    if (result.totalMatches >= options.maxMatches) {
      result.truncated = true;
      break;
    }
  }

  return result;
}

async function searchProjectBatches(
  projectRoot,
  request = {},
  onBatch = () => {},
  shouldCancel = () => false,
) {
  const query = normalizeQuery(request.query);
  const options = normalizeSearchOptions(request.options);
  const matcher = createMatcher(query, options);
  const candidates = searchCandidates(projectRoot, request);
  const batchSize = normalizeBatchSize(request);
  const summary = emptySearchResult(query, options);
  let batch = emptySearchResult(query, options);
  let scannedSinceYield = 0;

  async function flushBatch() {
    if (
      batch.scannedFiles === 0
      && batch.files.length === 0
      && batch.skippedFiles.length === 0
    ) {
      return;
    }
    await Promise.resolve(onBatch(batch));
    batch = emptySearchResult(query, options);
  }

  for (const file of candidates) {
    if (shouldCancel()) {
      summary.canceled = true;
      break;
    }

    const scan = scanSearchFile(projectRoot, file, matcher, options, summary);
    appendScanResult(summary, scan);
    appendScanResult(batch, scan);
    scannedSinceYield += scan.scanned || scan.skippedFile ? 1 : 0;

    if (summary.totalMatches >= options.maxMatches) {
      summary.truncated = true;
      batch.truncated = true;
      await flushBatch();
      break;
    }

    if (scannedSinceYield >= batchSize) {
      await flushBatch();
      scannedSinceYield = 0;
      await yieldToEventLoop();
    }
  }

  await flushBatch();
  return summary;
}

function replaceProjectMatches(projectRoot, request = {}) {
  const query = normalizeQuery(request.query);
  const replacement = String(request.replacement || "");
  const options = normalizeSearchOptions(request.options);
  const matcher = createMatcher(query, options);
  const targetFiles = Array.isArray(request.files) ? request.files : [];
  const allowedFiles = filterIgnoredCandidates(
    projectRoot,
    targetFiles.map(normalizeReplaceCandidate).filter(Boolean),
  );
  const allowedPaths = new Set(allowedFiles.map((file) => file.relativePath));
  const changedFiles = [];
  const conflicts = [];
  let replacements = 0;

  for (const file of targetFiles) {
    const relativePath = String(file && file.relativePath ? file.relativePath : "");
    const expectedHash = String(file && file.contentHash ? file.contentHash : "");
    const matches = Array.isArray(file && file.matches) ? file.matches : [];
    if (!relativePath || matches.length === 0) {
      continue;
    }
    if (!allowedPaths.has(relativePath)) {
      continue;
    }

    const target = resolveProjectFile(projectRoot, relativePath);
    const content = fs.readFileSync(target, "utf8");
    if (expectedHash && hashContent(content) !== expectedHash) {
      conflicts.push({ relativePath, reason: "stale-file" });
      continue;
    }

    const applied = applyMatchReplacements(content, matches, matcher, replacement, {
      trustedContentHash: Boolean(expectedHash),
    });
    if (applied.conflict) {
      conflicts.push({ relativePath, reason: applied.conflict });
      continue;
    }
    if (applied.count === 0) {
      continue;
    }

    fs.writeFileSync(target, applied.content, "utf8");
    changedFiles.push(relativePath);
    replacements += applied.count;
  }

  return {
    changedFiles,
    conflicts,
    replacements,
  };
}

function normalizeQuery(query) {
  const value = String(query || "");
  if (!value) {
    throw new Error("Search query is required");
  }
  return value;
}

function normalizeSearchOptions(options = {}) {
  return {
    caseSensitive: Boolean(options.caseSensitive),
    regexp: Boolean(options.regexp),
    wholeWord: Boolean(options.wholeWord),
    maxMatches: positiveInteger(options.maxMatches, DEFAULT_MAX_MATCHES),
    maxFileSizeBytes: positiveInteger(
      options.maxFileSizeBytes,
      DEFAULT_MAX_FILE_SIZE_BYTES,
    ),
  };
}

function normalizeBatchSize(request = {}) {
  return positiveInteger(
    request.batchSize || (request.options && request.options.batchSize),
    DEFAULT_BATCH_SIZE,
  );
}

function positiveInteger(value, fallback) {
  const number = Number(value);
  if (!Number.isFinite(number) || number <= 0) {
    return fallback;
  }
  return Math.floor(number);
}

function createMatcher(query, options) {
  const source = options.regexp ? query : escapeRegExp(query);
  const flags = options.caseSensitive ? "gu" : "giu";
  let pattern;
  try {
    pattern = new RegExp(source, flags);
  } catch (error) {
    throw new Error(`Invalid search regular expression: ${error.message}`);
  }
  return {
    pattern,
    regexp: options.regexp,
    wholeWord: options.wholeWord,
  };
}

function searchCandidates(projectRoot, request = {}) {
  const source = Array.isArray(request.candidates)
    ? request.candidates
    : listEditableFiles(projectRoot);
  const seen = new Set();
  const candidates = source
    .map(normalizeSearchCandidate)
    .filter((file) => {
      if (!file || seen.has(file.relativePath)) {
        return false;
      }
      seen.add(file.relativePath);
      return true;
    });
  if (request.candidatesRespectGitignore) {
    return candidates;
  }
  return filterIgnoredCandidates(projectRoot, candidates);
}

function prepareSearchCandidates(projectRoot, files = []) {
  return filterIgnoredCandidates(
    projectRoot,
    (Array.isArray(files) ? files : [])
      .map(normalizeSearchCandidate)
      .filter(Boolean),
  );
}

function normalizeSearchCandidate(file) {
  if (!file) {
    return null;
  }
  const relativePath = String(file.relativePath || file.path || "").trim();
  if (!relativePath) {
    return null;
  }
  const size = Number(file.size ?? file.bytes);
  const lineCount = Number(file.lineCount);
  return {
    relativePath,
    language: String(file.language || "plain"),
    size: Number.isFinite(size) && size >= 0 ? size : null,
    lineCount: Number.isFinite(lineCount) && lineCount >= 0 ? lineCount : null,
  };
}

function normalizeReplaceCandidate(file) {
  const candidate = normalizeSearchCandidate(file);
  if (!candidate) {
    return null;
  }
  return {
    ...candidate,
    matches: Array.isArray(file && file.matches) ? file.matches : [],
    contentHash: String(file && file.contentHash ? file.contentHash : ""),
  };
}

function filterIgnoredCandidates(projectRoot, candidates) {
  if (!Array.isArray(candidates) || candidates.length === 0) {
    return [];
  }
  const relativePaths = candidates.map((file) => file.relativePath);
  const gitIgnored = gitIgnoredPaths(projectRoot, relativePaths);
  const ignored = gitIgnored || fallbackGitignoreIgnoredPaths(projectRoot, relativePaths);
  if (!ignored || ignored.size === 0) {
    return candidates;
  }
  return candidates.filter((file) => !ignored.has(file.relativePath));
}

function gitIgnoredPaths(projectRoot, relativePaths) {
  if (!Array.isArray(relativePaths) || relativePaths.length === 0) {
    return new Set();
  }
  const ignored = new Set();
  for (let index = 0; index < relativePaths.length; index += GIT_CHECK_IGNORE_CHUNK_SIZE) {
    const chunk = relativePaths.slice(index, index + GIT_CHECK_IGNORE_CHUNK_SIZE);
    const result = spawnSync(
      "git",
      ["-C", projectRoot, "check-ignore", "--stdin", "-z"],
      {
        input: `${chunk.join("\0")}\0`,
        encoding: "utf8",
        maxBuffer: GIT_CHECK_IGNORE_MAX_BUFFER,
        stdio: ["pipe", "pipe", "ignore"],
      },
    );
    if (result.error || (result.status !== 0 && result.status !== 1)) {
      return null;
    }
    String(result.stdout || "")
      .split("\0")
      .filter(Boolean)
      .forEach((relativePath) => ignored.add(normalizeRelativePath(relativePath)));
  }
  return ignored;
}

function fallbackGitignoreIgnoredPaths(projectRoot, relativePaths) {
  const patterns = readRootGitignorePatterns(projectRoot);
  if (patterns.length === 0) {
    return new Set();
  }
  const ignored = new Set();
  for (const relativePath of relativePaths) {
    if (isIgnoredByPatterns(relativePath, patterns)) {
      ignored.add(relativePath);
    }
  }
  return ignored;
}

function readRootGitignorePatterns(projectRoot) {
  const gitignorePath = resolveProjectFile(projectRoot, ".gitignore");
  if (!fs.existsSync(gitignorePath) || !fs.statSync(gitignorePath).isFile()) {
    return [];
  }
  return fs.readFileSync(gitignorePath, "utf8")
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line && !line.startsWith("#"))
    .map((line) => ({
      negated: line.startsWith("!"),
      pattern: line.startsWith("!") ? line.slice(1) : line,
    }))
    .filter((entry) => entry.pattern);
}

function isIgnoredByPatterns(relativePath, patterns) {
  let ignored = false;
  for (const entry of patterns) {
    if (gitignorePatternMatches(entry.pattern, relativePath)) {
      ignored = !entry.negated;
    }
  }
  return ignored;
}

function gitignorePatternMatches(pattern, relativePath) {
  const normalizedPath = normalizeRelativePath(relativePath);
  const directoryOnly = pattern.endsWith("/");
  const anchored = pattern.startsWith("/");
  const body = normalizeRelativePath(pattern.replace(/^\/+/, "").replace(/\/+$/, ""));
  if (!body) {
    return false;
  }
  const pathParts = normalizedPath.split("/");
  if (!body.includes("/")) {
    return pathParts.some((part, index) => {
      if (!globPartMatches(body, part)) {
        return false;
      }
      return !directoryOnly || index < pathParts.length - 1;
    });
  }
  if (anchored) {
    return directoryOnly
      ? pathStartsWithPattern(normalizedPath, body)
      : globPathMatches(body, normalizedPath);
  }
  for (let index = 0; index < pathParts.length; index += 1) {
    const suffix = pathParts.slice(index).join("/");
    if (directoryOnly ? pathStartsWithPattern(suffix, body) : globPathMatches(body, suffix)) {
      return true;
    }
  }
  return false;
}

function pathStartsWithPattern(relativePath, pattern) {
  return relativePath === pattern
    || relativePath.startsWith(`${pattern}/`)
    || globPathMatches(`${pattern}/**`, relativePath);
}

function globPathMatches(pattern, relativePath) {
  return globToRegExp(pattern).test(relativePath);
}

function globPartMatches(pattern, value) {
  return globToRegExp(pattern).test(value);
}

function globToRegExp(pattern) {
  let source = "";
  for (let index = 0; index < pattern.length; index += 1) {
    const char = pattern[index];
    const next = pattern[index + 1];
    if (char === "*" && next === "*") {
      source += ".*";
      index += 1;
    } else if (char === "*") {
      source += "[^/]*";
    } else if (char === "?") {
      source += "[^/]";
    } else {
      source += escapeRegExp(char);
    }
  }
  return new RegExp(`^${source}$`);
}

function normalizeRelativePath(relativePath) {
  return String(relativePath || "").replace(/\\/g, "/").replace(/^\.\/+/, "");
}

function emptySearchResult(query, options) {
  return {
    query,
    options: {
      caseSensitive: options.caseSensitive,
      regexp: options.regexp,
      wholeWord: options.wholeWord,
      maxMatches: options.maxMatches,
      maxFileSizeBytes: options.maxFileSizeBytes,
    },
    scannedFiles: 0,
    matchedFiles: 0,
    totalMatches: 0,
    truncated: false,
    skippedFiles: [],
    files: [],
  };
}

function scanSearchFile(projectRoot, file, matcher, options, currentResult) {
  const target = resolveProjectFile(projectRoot, file.relativePath);
  const size = file.size === null ? fs.statSync(target).size : file.size;
  if (size > options.maxFileSizeBytes) {
    return {
      skippedFile: {
        relativePath: file.relativePath,
        reason: "file-too-large",
        size,
      },
    };
  }

  const content = fs.readFileSync(target, "utf8");
  const matches = findMatches(content, matcher, {
    remaining: options.maxMatches - currentResult.totalMatches,
  });

  return {
    scanned: true,
    matchCount: matches.length,
    file: matches.length > 0
      ? {
        relativePath: file.relativePath,
        language: file.language,
        size,
        contentHash: hashContent(content),
        matches,
      }
      : null,
  };
}

function appendScanResult(result, scan) {
  if (!scan) {
    return;
  }
  if (scan.skippedFile) {
    result.skippedFiles.push(scan.skippedFile);
  }
  if (scan.scanned) {
    result.scannedFiles += 1;
  }
  if (scan.file) {
    result.files.push(scan.file);
  }
  if (scan.matchCount) {
    result.totalMatches += scan.matchCount;
  }
  result.matchedFiles = result.files.length;
}

function findMatches(content, matcher, limits) {
  const matches = [];
  if (!limits || limits.remaining <= 0) {
    return matches;
  }
  const lineStarts = lineStartOffsets(content);
  matcher.pattern.lastIndex = 0;

  let match;
  while ((match = matcher.pattern.exec(content)) !== null) {
    if (match[0] === "") {
      throw new Error("Search pattern cannot match empty text");
    }

    const start = match.index;
    const end = start + match[0].length;
    if (!matcher.wholeWord || isWholeWordMatch(content, start, end)) {
      matches.push(matchResult(content, lineStarts, matches.length, start, end));
      if (matches.length >= limits.remaining) {
        break;
      }
    }
  }

  return matches;
}

function matchResult(content, lineStarts, index, start, end) {
  const line = lineNumberForOffset(lineStarts, start);
  const lineStart = lineStarts[line - 1];
  const lineEnd = nextLineStart(content, lineStarts, line) - 1;
  const matchText = content.slice(start, end);
  return {
    index,
    line,
    column: start - lineStart + 1,
    start,
    end,
    matchText: boundedMatchText(matchText),
    matchTextTruncated: matchText.length > MAX_MATCH_TEXT_CHARS,
    preview: matchPreview(content, lineStart, Math.max(lineStart, lineEnd), start, end),
  };
}

function matchPreview(content, lineStart, lineEnd, start, end) {
  const lineLength = lineEnd - lineStart;
  if (lineLength <= MAX_MATCH_PREVIEW_CHARS) {
    return content.slice(lineStart, lineEnd);
  }

  const prefix = start - MATCH_PREVIEW_CONTEXT_CHARS > lineStart ? "..." : "";
  const suffix = end + MATCH_PREVIEW_CONTEXT_CHARS < lineEnd ? "..." : "";
  const budget = Math.max(
    1,
    MAX_MATCH_PREVIEW_CHARS - prefix.length - suffix.length,
  );
  const desiredStart = Math.max(lineStart, start - MATCH_PREVIEW_CONTEXT_CHARS);
  const desiredEnd = Math.min(lineEnd, desiredStart + budget);
  return `${prefix}${content.slice(desiredStart, desiredEnd)}${suffix}`;
}

function boundedMatchText(matchText) {
  if (matchText.length <= MAX_MATCH_TEXT_CHARS) {
    return matchText;
  }
  return matchText.slice(0, MAX_MATCH_TEXT_CHARS);
}

function applyMatchReplacements(content, matches, matcher, replacement, options = {}) {
  const orderedMatches = matches
    .map((match) => ({
      start: Number(match.start),
      end: Number(match.end),
      matchText: String(match.matchText || ""),
      matchTextTruncated: Boolean(match.matchTextTruncated),
    }))
    .filter((match) => (
      Number.isInteger(match.start)
      && Number.isInteger(match.end)
      && match.start >= 0
      && match.end > match.start
      && match.end <= content.length
    ))
    .sort((left, right) => right.start - left.start);

  let nextContent = content;
  let count = 0;
  for (const match of orderedMatches) {
    const actual = nextContent.slice(match.start, match.end);
    if (match.matchTextTruncated && !options.trustedContentHash) {
      return { conflict: "match-mismatch" };
    }
    if (!match.matchTextTruncated && actual !== match.matchText) {
      return { conflict: "match-mismatch" };
    }
    const insert = replacementForMatch(actual, matcher, replacement);
    nextContent = `${nextContent.slice(0, match.start)}${insert}${nextContent.slice(match.end)}`;
    count += 1;
  }

  return { content: nextContent, count };
}

function replacementForMatch(matchText, matcher, replacement) {
  if (!matcher.regexp) {
    return replacement;
  }
  const source = matcher.pattern.source;
  const flags = matcher.pattern.flags.replace(/g/g, "");
  const pattern = new RegExp(source, flags);
  return matchText.replace(pattern, replacement);
}

function lineStartOffsets(content) {
  const starts = [0];
  for (let i = 0; i < content.length; i += 1) {
    if (content[i] === "\n") {
      starts.push(i + 1);
    }
  }
  return starts;
}

function lineNumberForOffset(lineStarts, offset) {
  let low = 0;
  let high = lineStarts.length - 1;
  while (low <= high) {
    const mid = Math.floor((low + high) / 2);
    if (lineStarts[mid] <= offset) {
      low = mid + 1;
    } else {
      high = mid - 1;
    }
  }
  return high + 1;
}

function nextLineStart(content, lineStarts, line) {
  if (line < lineStarts.length) {
    return lineStarts[line];
  }
  return content.length + 1;
}

function isWholeWordMatch(content, start, end) {
  return !isWordChar(content[start - 1]) && !isWordChar(content[end]);
}

function isWordChar(char) {
  return Boolean(char && /[\p{L}\p{N}_]/u.test(char));
}

function escapeRegExp(value) {
  return String(value).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function hashContent(content) {
  return crypto.createHash("sha256").update(content, "utf8").digest("hex");
}

function yieldToEventLoop() {
  return new Promise((resolve) => setImmediate(resolve));
}

module.exports = {
  prepareSearchCandidates,
  replaceProjectMatches,
  searchProjectBatches,
  searchProject,
};
