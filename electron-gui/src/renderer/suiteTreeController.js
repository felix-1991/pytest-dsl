import { renderVirtualTreeRows } from "./treeVirtualizer.js";
import { escapeAttr, escapeHtml } from "./utils.js";

export function createSuiteTreeController({
  state,
  el,
  currentCommand,
  previewCommand,
  selectedConfigSources,
  updateBuildSummary,
  updateDebugActionState = () => {},
}) {
  function ensureBuildCaseTreeExpanded() {
    if (!state.snapshot || !state.snapshot.suiteTree) {
      return;
    }
    collectSuiteDirectoryPaths(state.snapshot.suiteTree).forEach((nodePath) => {
      state.expandedSuiteNodes.add(nodePath);
    });
  }

  function ensureBuildCaseTreeRootExpanded() {
    if (!state.snapshot) {
      return;
    }
    const tree = state.snapshot.suiteTree || buildFlatSuiteTree(state.snapshot.suites || []);
    if (tree && tree.path) {
      state.expandedSuiteNodes.add(tree.path);
    }
  }

  function buildCaseTreeRenderSignature() {
    if (!state.snapshot) {
      return "empty";
    }
    const suiteKey = (state.snapshot.suites || [])
      .map((suite) => `${suite.id}:${suite.rootPath || ""}`)
      .join("|");
    const expandedKey = [...state.expandedSuiteNodes].sort().join("|");
    return [
      state.snapshot.project && state.snapshot.project.rootPath,
      suiteKey,
      state.buildCaseFilter,
      expandedKey,
    ].join("\n");
  }

  function invalidateBuildCaseTreeRender() {
    state.buildCaseTreeSignature = null;
  }

  function ensureBuildCaseTreeRendered() {
    const signature = buildCaseTreeRenderSignature();
    if (state.buildCaseTreeSignature === signature) {
      return;
    }
    renderBuildCaseTree();
  }

  function scheduleBuildCaseTreeRender() {
    invalidateBuildCaseTreeRender();
    if (state.buildCaseTreeRenderScheduled) {
      return;
    }
    state.buildCaseTreeRenderScheduled = true;
    const flush = () => {
      state.buildCaseTreeRenderRaf = null;
      state.buildCaseTreeRenderTimer = null;
      state.buildCaseTreeRenderScheduled = false;
      ensureBuildCaseTreeRendered();
    };
    if (typeof window.requestAnimationFrame === "function") {
      state.buildCaseTreeRenderRaf = window.requestAnimationFrame(flush);
    } else {
      state.buildCaseTreeRenderTimer = window.setTimeout(flush, 0);
    }
  }

  function setAllBuildCaseGroupsExpanded(expanded) {
    if (!state.snapshot || !state.snapshot.suiteTree) {
      return;
    }
    if (expanded) {
      ensureBuildCaseTreeExpanded();
    } else {
      collectSuiteDirectoryPaths(state.snapshot.suiteTree).forEach((nodePath) => {
        state.expandedSuiteNodes.delete(nodePath);
      });
    }
    invalidateBuildCaseTreeRender();
    ensureBuildCaseTreeRendered();
  }

  function collectSuiteDirectoryPaths(node) {
    if (!node || node.type === "file") {
      return [];
    }
    return [
      node.path,
      ...(node.children || []).flatMap(collectSuiteDirectoryPaths),
    ].filter(Boolean);
  }

  function renderSuiteOptions(suites, suiteTree = null) {
    const availableSuites = Array.isArray(suites) ? suites : [];
    const ids = availableSuites.map((suite) => suite.id);
    const previous = state.selectedSuiteIds.filter((id) => ids.includes(id));
    const previousBuild = state.selectedBuildSuiteIds.filter((id) => ids.includes(id));
    state.selectedSuiteIds = state.suiteSelectionTouched ? previous : ids;
    state.selectedBuildSuiteIds = state.buildSelectionTouched ? previousBuild : ids;
    updateSuiteSummary(availableSuites);
    renderDebugSuiteTree(availableSuites, suiteTree);
    if (state.activeView === "build") {
      invalidateBuildCaseTreeRender();
      ensureBuildCaseTreeRendered();
    } else {
      invalidateBuildCaseTreeRender();
    }
    previewCommand(currentCommand());
    updateDebugActionState();
  }

  function renderDebugSuiteTree(suites = null, suiteTree = null) {
    const availableSuites = Array.isArray(suites)
      ? suites
      : (state.snapshot ? state.snapshot.suites || [] : []);
    const tree = suiteTree || (state.snapshot && state.snapshot.suiteTree) || buildFlatSuiteTree(availableSuites);
    el.suiteList.innerHTML =
      availableSuites.length === 0
        ? `<p class="empty">未找到 convention 测试套</p>`
        : renderSuiteTreeNode(tree, 0, "debug");
    bindSuiteTreeEvents(el.suiteList);
    syncSuiteTreeCheckboxStates("debug");
  }

  function renderBuildCaseTree() {
    const signature = buildCaseTreeRenderSignature();
    if (!state.snapshot) {
      el.buildCaseTree.innerHTML = `<p class="empty">打开项目后显示可构建案例</p>`;
      state.buildCaseTreeSignature = signature;
      return;
    }

    const suites = state.snapshot.suites || [];
    if (suites.length === 0) {
      el.buildCaseTree.innerHTML = `<p class="empty">未找到 convention 测试套</p>`;
      state.buildCaseTreeSignature = signature;
      return;
    }

    const tree = filteredSuiteTree(state.snapshot.suiteTree || buildFlatSuiteTree(suites), state.buildCaseFilter);
    if (!tree) {
      el.buildCaseTree.innerHTML = `<p class="empty">没有匹配的构建案例</p>`;
      state.buildCaseTreeSignature = signature;
      return;
    }

    const rows = flattenVisibleSuiteTreeRows(tree, "build");
    renderVirtualTreeRows(el.buildCaseTree, rows, renderSuiteTreeRow);
    syncSuiteTreeCheckboxStates("build");
    state.buildCaseTreeSignature = signature;
  }

  function bindSuiteTreeEvents(container) {
    return container;
  }

  function filteredSuiteTree(node, filter) {
    if (!node) {
      return null;
    }
    const query = String(filter || "").trim().toLowerCase();
    if (!query) {
      return node;
    }

    const label = [
      node.name,
      node.path,
      node.rootPath,
      node.filePath,
      node.suiteId,
    ].filter(Boolean).join(" ").toLowerCase();
    const children = (node.children || [])
      .map((child) => filteredSuiteTree(child, query))
      .filter(Boolean);
    if (label.includes(query) || children.length > 0) {
      return {
        ...node,
        children,
      };
    }
    return null;
  }

  function renderSuiteTreeNode(node, depth = 0, scope = "debug") {
    if (!node) {
      return "";
    }

    if (node.type === "file") {
      const isChecked = isFileSelected(node.suiteId, node.path, scope);
      const fileCheckedStr = isChecked ? " checked" : "";
      const fileIcon = node.fileType === "dsl" ? "DSL" : "PY";
      return `
        <div class="suite-node suite-file-node" style="--depth: ${depth}">
          <label class="suite-option is-file">
            <span class="suite-spacer"></span>
            <input type="checkbox" data-file-checkbox
                   data-suite-scope="${escapeAttr(scope)}"
                   data-suite-id="${escapeAttr(node.suiteId || "")}"
                   data-file-path="${escapeAttr(node.path || "")}"${fileCheckedStr}>
            <span class="file-icon">${fileIcon}</span>
            <span title="${escapeAttr(node.path)}">${escapeHtml(node.name)}</span>
          </label>
        </div>
      `;
    }

    const suiteId = node.suiteId;
    const suiteIds = collectSuiteNodeSuiteIds(node);
    const checked = suiteIds.length > 0 && suiteIds.every((id) => selectedSuiteIdsForScope(scope).includes(id))
      ? " checked"
      : "";
    const counts = `${node.dslCaseCount || 0} DSL / ${node.pythonTestCount || 0} py`;
    const label = suiteId === "__root__" ? "根目录" : node.name;

    const hasChildren = node.children && node.children.length > 0;
    const isExpanded = state.expandedSuiteNodes.has(node.path);

    const toggleArrow = hasChildren
      ? `<span class="suite-toggle ${isExpanded ? "is-open" : ""}" data-suite-toggle="${escapeAttr(node.path)}">▶</span>`
      : `<span class="suite-spacer"></span>`;

    return `
      <div class="suite-node" style="--depth: ${depth}">
        <label class="suite-option${suiteId ? "" : " is-group"}">
          ${toggleArrow}
          ${suiteIds.length > 0
            ? `<input type="checkbox" data-suite-checkbox data-suite-scope="${escapeAttr(scope)}" data-suite-id="${escapeAttr(suiteId || "")}" data-suite-ids="${escapeAttr(JSON.stringify(suiteIds))}"${checked}>`
            : `<span class="suite-spacer"></span>`}
          <span title="${escapeAttr(node.rootPath || node.path || label)}">${escapeHtml(label)}</span>
          <small>${suiteId ? escapeHtml(counts) : ""}</small>
        </label>
        ${hasChildren ? `
          <div class="suite-children ${isExpanded ? "" : "is-collapsed"}">
            ${isExpanded ? (node.children || []).map((child) => renderSuiteTreeNode(child, depth + 1, scope)).join("") : ""}
          </div>
        ` : ""}
      </div>
    `;
  }

  function flattenVisibleSuiteTreeRows(root, scope = "debug") {
    const rows = [];
    const visit = (node, depth) => {
      if (!node) {
        return;
      }
      rows.push({ node, depth, scope });
      if (node.type !== "file" && state.expandedSuiteNodes.has(node.path)) {
        (node.children || []).forEach((child) => visit(child, depth + 1));
      }
    };
    visit(root, 0);
    return rows;
  }

  function renderSuiteTreeRow(row) {
    const node = row && row.node;
    const depth = row ? row.depth : 0;
    const scope = row ? row.scope : "debug";
    if (!node) {
      return "";
    }

    if (node.type === "file") {
      const isChecked = isFileSelected(node.suiteId, node.path, scope);
      const fileCheckedStr = isChecked ? " checked" : "";
      const fileIcon = node.fileType === "dsl" ? "DSL" : "PY";
      return `
        <div class="suite-node suite-file-node" style="--depth: ${depth}">
          <label class="suite-option is-file">
            <span class="suite-spacer"></span>
            <input type="checkbox" data-file-checkbox
                   data-suite-scope="${escapeAttr(scope)}"
                   data-suite-id="${escapeAttr(node.suiteId || "")}"
                   data-file-path="${escapeAttr(node.path || "")}"${fileCheckedStr}>
            <span class="file-icon">${fileIcon}</span>
            <span title="${escapeAttr(node.path)}">${escapeHtml(node.name)}</span>
          </label>
        </div>
      `;
    }

    const suiteId = node.suiteId;
    const suiteIds = collectSuiteNodeSuiteIds(node);
    const checked = suiteIds.length > 0 && suiteIds.every((id) => selectedSuiteIdsForScope(scope).includes(id))
      ? " checked"
      : "";
    const counts = `${node.dslCaseCount || 0} DSL / ${node.pythonTestCount || 0} py`;
    const label = suiteId === "__root__" ? "根目录" : node.name;
    const hasChildren = node.children && node.children.length > 0;
    const isExpanded = state.expandedSuiteNodes.has(node.path);
    const toggleArrow = hasChildren
      ? `<span class="suite-toggle ${isExpanded ? "is-open" : ""}" data-suite-toggle="${escapeAttr(node.path)}">▶</span>`
      : `<span class="suite-spacer"></span>`;

    return `
      <div class="suite-node" style="--depth: ${depth}">
        <label class="suite-option${suiteId ? "" : " is-group"}">
          ${toggleArrow}
          ${suiteIds.length > 0
            ? `<input type="checkbox" data-suite-checkbox data-suite-scope="${escapeAttr(scope)}" data-suite-id="${escapeAttr(suiteId || "")}" data-suite-ids="${escapeAttr(JSON.stringify(suiteIds))}"${checked}>`
            : `<span class="suite-spacer"></span>`}
          <span title="${escapeAttr(node.rootPath || node.path || label)}">${escapeHtml(label)}</span>
          <small>${suiteId ? escapeHtml(counts) : ""}</small>
        </label>
      </div>
    `;
  }

  function buildFlatSuiteTree(suites) {
    return {
      type: "directory",
      path: "tests",
      name: "tests",
      suiteId: null,
      children: suites.map((suite) => ({
        ...suite,
        type: "directory",
        path: suite.id,
        suiteId: suite.id,
        children: [],
      })),
    };
  }

  function handleSuiteSelectionChange(event) {
    const input = event.currentTarget;
    const scope = input.dataset.suiteScope || "debug";
    markSuiteSelectionTouched(scope);
    const suiteIds = suiteIdsFromSuiteInput(input);
    const selected = new Set(selectedSuiteIdsForScope(scope));
    const overrides = selectedFileOverridesForScope(scope);

    suiteIds.forEach((suiteId) => {
      if (input.checked) {
        selected.add(suiteId);
      } else {
        selected.delete(suiteId);
      }
      delete overrides[suiteId];
    });

    setSelectedSuiteIdsForScope(scope, [...selected]);
    syncSuiteTreeCheckboxStates(scope);
    updateSuiteSummary(state.snapshot ? state.snapshot.suites || [] : []);
    updateBuildSummary();
    previewCommand(currentCommand(), { force: true });
    updateDebugActionState();
  }

  function handleFileSelectionChange(event) {
    const input = event.currentTarget;
    const scope = input.dataset.suiteScope || "debug";
    markSuiteSelectionTouched(scope);
    const suiteId = input.dataset.suiteId;
    const filePath = input.dataset.filePath;
    const selectedSuiteIds = selectedSuiteIdsForScope(scope);
    const overrides = selectedFileOverridesForScope(scope);

    if (!overrides[suiteId]) {
      const isSuiteSelected = selectedSuiteIds.includes(suiteId);
      const files = getSuiteFiles(suiteId);
      if (isSuiteSelected) {
        overrides[suiteId] = new Set(files);
      } else {
        overrides[suiteId] = new Set();
      }
    }

    if (input.checked) {
      overrides[suiteId].add(filePath);
    } else {
      overrides[suiteId].delete(filePath);
    }

    syncSuiteCheckboxFromFiles(suiteId, scope);
    syncSuiteTreeCheckboxStates(scope);
    updateSuiteSummary(state.snapshot ? state.snapshot.suites || [] : []);
    updateBuildSummary();

    previewCommand(currentCommand(), { force: true });
    updateDebugActionState();
  }

  function handleSuiteTreeChange(event) {
    const input = event.target && typeof event.target.closest === "function"
      ? event.target.closest("[data-suite-checkbox], [data-file-checkbox]")
      : null;
    if (!input || !event.currentTarget.contains(input)) {
      return;
    }
    if (input.hasAttribute("data-suite-checkbox")) {
      handleSuiteSelectionChange({ currentTarget: input });
      return;
    }
    handleFileSelectionChange({ currentTarget: input });
  }

  function handleSuiteTreeClick(event) {
    const toggle = event.target && typeof event.target.closest === "function"
      ? event.target.closest("[data-suite-toggle]")
      : null;
    if (!toggle || !event.currentTarget.contains(toggle)) {
      return;
    }
    event.stopPropagation();
    event.preventDefault();
    toggleSuiteTreeNode(toggle);
  }

  function handleSuiteToggleClick(event) {
    event.stopPropagation();
    event.preventDefault();
    toggleSuiteTreeNode(event.currentTarget);
  }

  function toggleSuiteTreeNode(toggle) {
    const path = toggle.dataset.suiteToggle;
    const scope = suiteScopeFromElement(toggle);
    if (!path) {
      return;
    }

    if (state.expandedSuiteNodes.has(path)) {
      state.expandedSuiteNodes.delete(path);
    } else {
      state.expandedSuiteNodes.add(path);
    }

    if (scope === "build") {
      invalidateBuildCaseTreeRender();
      ensureBuildCaseTreeRendered();
      return;
    }

    renderDebugSuiteTree();
  }

  function syncSuiteCheckboxFromFiles(suiteId, scope = "debug") {
    const files = getSuiteFiles(suiteId);
    const selectedSuiteIds = selectedSuiteIdsForScope(scope);
    const overrides = selectedFileOverridesForScope(scope);
    const override = overrides[suiteId];

    if (override) {
      if (override.size === 0) {
        setSelectedSuiteIdsForScope(scope, selectedSuiteIds.filter((id) => id !== suiteId));
      } else {
        if (!selectedSuiteIds.includes(suiteId)) {
          setSelectedSuiteIdsForScope(scope, [...selectedSuiteIds, suiteId]);
        }
        if (override.size === files.length) {
          delete overrides[suiteId];
        }
      }
    }
  }

  function collectSuiteNodeSuiteIds(node) {
    if (!node || node.type === "file") {
      return [];
    }
    return [
      node.suiteId,
      ...(node.children || []).filter((child) => child.type !== "file").flatMap(collectSuiteNodeSuiteIds),
    ].filter(Boolean);
  }

  function syncSuiteTreeCheckboxStates(scope = null) {
    suiteTreeContainers(scope).forEach((container) => {
      container.querySelectorAll("[data-file-checkbox]").forEach((input) => {
        const scope = input.dataset.suiteScope || "debug";
        const suiteId = input.dataset.suiteId;
        const filePath = input.dataset.filePath;
        input.checked = isFileSelected(suiteId, filePath, scope);
      });

      container.querySelectorAll("[data-suite-checkbox]").forEach((input) => {
        const suiteIds = suiteIdsFromSuiteInput(input);
        const scope = input.dataset.suiteScope || "debug";
        const selectedSuiteIds = selectedSuiteIdsForScope(scope);
        const overrides = selectedFileOverridesForScope(scope);

        if (suiteIds.length === 0) {
          input.checked = false;
          input.indeterminate = false;
          return;
        }

        let totalFilesCount = 0;
        let selectedFilesCount = 0;
        let anySuiteChecked = false;
        let anySuiteUnchecked = false;
        let anySuitePartial = false;

        suiteIds.forEach((id) => {
          const isSuiteSelected = selectedSuiteIds.includes(id);
          const files = getSuiteFiles(id);

          if (files.length === 0) {
            if (isSuiteSelected) {
              anySuiteChecked = true;
            } else {
              anySuiteUnchecked = true;
            }
            return;
          }

          totalFilesCount += files.length;

          if (!isSuiteSelected) {
            anySuiteUnchecked = true;
            return;
          }

          const override = overrides[id];
          if (!override) {
            selectedFilesCount += files.length;
            anySuiteChecked = true;
          } else {
            selectedFilesCount += override.size;
            if (override.size === files.length) {
              anySuiteChecked = true;
            } else if (override.size === 0) {
              anySuiteUnchecked = true;
            } else {
              anySuitePartial = true;
            }
          }
        });

        let checked = false;
        let indeterminate = false;

        if (totalFilesCount > 0) {
          checked = (selectedFilesCount === totalFilesCount);
          indeterminate = (selectedFilesCount > 0 && selectedFilesCount < totalFilesCount);
        } else {
          checked = anySuiteChecked && !anySuiteUnchecked;
          indeterminate = anySuiteChecked && anySuiteUnchecked;
        }

        if (anySuitePartial) {
          indeterminate = true;
          checked = false;
        }

        input.checked = checked;
        input.indeterminate = indeterminate;
        input.closest(".suite-option")?.classList.toggle("is-partial", indeterminate);
      });
    });
  }

  function suiteTreeContainers(scope = null) {
    if (scope === "debug") {
      return [el.suiteList].filter(Boolean);
    }
    if (scope === "build") {
      return [el.buildCaseTree].filter(Boolean);
    }
    return [el.suiteList, el.buildCaseTree].filter(Boolean);
  }

  function suiteScopeFromElement(element) {
    const scopedElement = element && typeof element.closest === "function"
      ? element.closest("[data-suite-scope]")
      : null;
    if (scopedElement && scopedElement.dataset.suiteScope) {
      return scopedElement.dataset.suiteScope;
    }
    if (el.buildCaseTree && el.buildCaseTree.contains(element)) {
      return "build";
    }
    if (el.suiteList && el.suiteList.contains(element)) {
      return "debug";
    }
    return activeSuiteSelectionScope();
  }

  function activeSuiteSelectionScope() {
    return state.activeView === "build" ? "build" : "debug";
  }

  function selectedSuiteIdsForScope(scope = "debug") {
    return scope === "build" ? state.selectedBuildSuiteIds : state.selectedSuiteIds;
  }

  function setSelectedSuiteIdsForScope(scope, suiteIds) {
    if (scope === "build") {
      state.selectedBuildSuiteIds = normalizeSelectedSuiteIds(suiteIds);
      return;
    }
    state.selectedSuiteIds = normalizeSelectedSuiteIds(suiteIds);
  }

  function selectedFileOverridesForScope(scope = "debug") {
    return scope === "build" ? state.selectedBuildFileOverrides : state.selectedFileOverrides;
  }

  function markSuiteSelectionTouched(scope = "debug") {
    if (scope === "build") {
      state.buildSelectionTouched = true;
      return;
    }
    state.suiteSelectionTouched = true;
  }

  function suiteIdsFromSuiteInput(input) {
    try {
      const parsed = JSON.parse(input.dataset.suiteIds || "[]");
      return Array.isArray(parsed) ? parsed.filter(Boolean) : [];
    } catch (_error) {
      return [];
    }
  }

  function normalizeSelectedSuiteIds(suiteIds) {
    const selected = new Set(Array.isArray(suiteIds) ? suiteIds : []);
    return availableSuiteIds().filter((suiteId) => selected.has(suiteId));
  }

  function availableSuiteIds() {
    if (!state.snapshot || !Array.isArray(state.snapshot.suites)) {
      return [];
    }
    return state.snapshot.suites.map((suite) => suite.id);
  }

  function updateSuiteSummary(suites) {
    const total = Array.isArray(suites) ? suites.length : 0;
    const selected = currentSelectedSuiteIds("debug");
    if (total === 0) {
      el.suiteSummary.textContent = "无测试套";
      return;
    }
    if (selected.length === 0) {
      el.suiteSummary.textContent = "未选择测试套";
      return;
    }

    let hasOverride = false;
    let totalFiles = 0;
    let selectedFiles = 0;

    selected.forEach((suiteId) => {
      const files = getSuiteFiles(suiteId);
      totalFiles += files.length;

      const override = state.selectedFileOverrides[suiteId];
      if (override) {
        hasOverride = true;
        selectedFiles += override.size;
      } else {
        selectedFiles += files.length;
      }
    });

    if (selected.length === total) {
      if (!hasOverride) {
        el.suiteSummary.textContent = `全部测试套 (${total})`;
      } else {
        el.suiteSummary.textContent = `全部测试套 (${selectedFiles}/${totalFiles} 文件)`;
      }
      return;
    }

    if (selected.length === 1) {
      const suite = suites.find((item) => item.id === selected[0]);
      const name = suite ? suiteDisplayName(suite) : selected[0];
      const override = state.selectedFileOverrides[selected[0]];
      if (override) {
        const files = getSuiteFiles(selected[0]);
        el.suiteSummary.textContent = `${name} (${override.size}/${files.length} 文件)`;
      } else {
        el.suiteSummary.textContent = name;
      }
      return;
    }

    if (hasOverride) {
      el.suiteSummary.textContent = `${selected.length}/${total} 已选 · 部分文件`;
    } else {
      el.suiteSummary.textContent = `${selected.length}/${total} 已选`;
    }
  }

  function currentSelectedSuiteIds(scope = activeSuiteSelectionScope()) {
    if (!state.snapshot || !Array.isArray(state.snapshot.suites)) {
      return [];
    }
    const availableIds = state.snapshot.suites.map((suite) => suite.id);
    return selectedSuiteIdsForScope(scope).filter((id) => availableIds.includes(id));
  }

  function suiteCommandLabel(selectedSuiteIds, yamlVars, scope = "debug") {
    const selectedFiles = computeSelectedFiles(scope);
    const targets = selectedFiles ? selectedFiles : suiteTargetPathsForSelection(selectedSuiteIds);
    const suiteLabel = targets.length > 0
      ? targets.join(" ")
      : "<未选择测试套>";
    const args = yamlVars.length > 0
      ? ` ${yamlVars.map((item) => `--yaml-vars ${item}`).join(" ")}`
      : "";
    return `pytest ${suiteLabel}${args}`;
  }

  function buildCommandLabel(buildId = null) {
    const yamlVars = selectedConfigSources().map((source) => source.relativePath);
    const selectedFiles = computeSelectedFiles("build");
    const targets = selectedFiles ? selectedFiles : suiteTargetPathsForSelection(currentSelectedSuiteIds("build"));
    const targetLabel = targets.length > 0
      ? targets.join(" ")
      : "<未选择测试套>";
    const resultsDir = buildResultsDirForBuild(buildId || "<build-id>");
    const args = yamlVars.length > 0
      ? ` ${yamlVars.map((item) => `--yaml-vars ${item}`).join(" ")}`
      : "";
    return `pytest ${targetLabel} --alluredir ${resultsDir}${args}`;
  }

  function buildPytestArgsLabel(yamlVars, buildId = null) {
    const args = [
      "--alluredir",
      buildResultsDirForBuild(buildId || "<build-id>"),
      ...yamlVars.flatMap((item) => ["--yaml-vars", item]),
    ];
    return args.join(" ");
  }

  function activeBuildCommandId() {
    return state.currentTaskMode === "build" ? state.currentBuildId : null;
  }

  function buildResultsDirForBuild(buildId) {
    return `.pytest-dsl-gui/builds/${buildId}/allure-results`;
  }

  function suiteBuildScopeLabel(selectedSuiteIds, scope = "build") {
    const selectedFiles = computeSelectedFiles(scope);
    if (selectedFiles && selectedFiles.length > 0) {
      return `${selectedFiles.length} 文件`;
    }
    const targets = suiteTargetPathsForSelection(selectedSuiteIds);
    return targets.length > 0 ? targets.join(" ") : "未选择测试套";
  }

  function computeSelectedFiles(scope = activeSuiteSelectionScope()) {
    const selectedFiles = [];
    const selectedSuiteIds = currentSelectedSuiteIds(scope);
    const overrides = selectedFileOverridesForScope(scope);
    let hasOverride = false;

    selectedSuiteIds.forEach((suiteId) => {
      const override = overrides[suiteId];
      if (override) {
        hasOverride = true;
        override.forEach((file) => {
          selectedFiles.push(file);
        });
      } else {
        const files = getSuiteFiles(suiteId);
        files.forEach((file) => {
          selectedFiles.push(file);
        });
      }
    });

    return hasOverride ? selectedFiles : null;
  }

  function isFileSelected(suiteId, filePath, scope = "debug") {
    const isSuiteSelected = selectedSuiteIdsForScope(scope).includes(suiteId);
    if (!isSuiteSelected) {
      return false;
    }
    const override = selectedFileOverridesForScope(scope)[suiteId];
    if (!override) {
      return true;
    }
    return override.has(filePath);
  }

  function getSuiteFiles(suiteId) {
    if (!state.snapshot || !Array.isArray(state.snapshot.suites)) {
      return [];
    }
    const suite = state.snapshot.suites.find((suite) => suite.id === suiteId);
    if (!suite) {
      return [];
    }
    return (suite.dslCaseFiles || []).concat(suite.pythonTestFiles || []);
  }

  function suiteTargetPathsForSelection(selectedSuiteIds) {
    const selected = Array.isArray(selectedSuiteIds) ? selectedSuiteIds : [];
    if (selected.length === 0) {
      return [];
    }
    if (selected.includes("all")) {
      return ["tests"];
    }
    if (!state.snapshot || !Array.isArray(state.snapshot.suites)) {
      return selected;
    }

    const suitesById = new Map(state.snapshot.suites.map((suite) => [suite.id, suite]));
    const targets = selected
      .map((suiteId) => suitesById.get(suiteId))
      .filter(Boolean)
      .map((suite) => suite.rootPath || suite.id)
      .filter(Boolean);
    return compactRelativeTargets(targets);
  }

  function compactRelativeTargets(paths) {
    const unique = [...new Set(paths.map((item) => String(item || "").replace(/\\/g, "/")).filter(Boolean))]
      .sort((left, right) => {
        const depthDiff = left.split("/").length - right.split("/").length;
        return depthDiff || left.localeCompare(right);
      });
    const compacted = [];
    unique.forEach((target) => {
      if (!compacted.some((selected) => target === selected || target.startsWith(`${selected}/`))) {
        compacted.push(target);
      }
    });
    return compacted;
  }

  function suiteDisplayName(suite) {
    if (!suite) {
      return "";
    }
    return suite.id === "__root__" ? "根目录 (__root__)" : suite.name || suite.id;
  }

  function groupFilesByDirectory(files) {
    const byDirectory = new Map();
    files.forEach((file) => {
      const directory = file.directory || ".";
      if (!byDirectory.has(directory)) {
        byDirectory.set(directory, []);
      }
      byDirectory.get(directory).push(file);
    });
    return Array.from(byDirectory.entries()).map(([name, groupFiles]) => ({
      name,
      files: groupFiles,
    }));
  }

  return {
    activeBuildCommandId,
    buildCommandLabel,
    buildPytestArgsLabel,
    buildResultsDirForBuild,
    computeSelectedFiles,
    currentSelectedSuiteIds,
    ensureBuildCaseTreeRendered,
    ensureBuildCaseTreeRootExpanded,
    groupFilesByDirectory,
    handleSuiteToggleClick,
    handleSuiteTreeChange,
    handleSuiteTreeClick,
    invalidateBuildCaseTreeRender,
    renderBuildCaseTree,
    renderDebugSuiteTree,
    renderSuiteOptions,
    scheduleBuildCaseTreeRender,
    setAllBuildCaseGroupsExpanded,
    suiteBuildScopeLabel,
    suiteCommandLabel,
  };
}
