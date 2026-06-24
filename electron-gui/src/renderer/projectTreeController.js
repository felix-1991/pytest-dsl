import { renderVirtualTreeRows } from "./treeVirtualizer.js";
import {
  clamp,
  cssEscape,
  errorMessage,
  escapeAttr,
  escapeHtml,
  fileNameFromPath,
} from "./utils.js";

export function createProjectTreeController({
  state,
  el,
  api,
  appendLog,
  fileIcon,
  fileKind,
  folderIcon,
  refreshProject,
  selectFile,
}) {
  function scheduleFileTreeRender() {
    if (state.fileTreeRenderScheduled) {
      return;
    }
    state.fileTreeRenderScheduled = true;
    const flush = () => {
      state.fileTreeRenderRaf = null;
      state.fileTreeRenderTimer = null;
      state.fileTreeRenderScheduled = false;
      renderFileTree();
    };
    if (typeof window.requestAnimationFrame === "function") {
      state.fileTreeRenderRaf = window.requestAnimationFrame(flush);
    } else {
      state.fileTreeRenderTimer = window.setTimeout(flush, 0);
    }
  }

  function handleProjectTreeScroll() {
    closeTreeContextMenu();
    scheduleFileTreeRender();
  }

  function renderFileTree() {
    if (!state.snapshot) {
      return;
    }

    const tree = filterProjectTree(state.snapshot.tree, state.filter);
    const rows = flattenVisibleProjectTreeRows(tree);
    if (rows.length === 0) {
      el.fileTree.innerHTML = `<p class="empty">${state.filter ? "没有匹配的文件或目录" : "项目中没有可编辑文本文件"}</p>`;
      return;
    }

    renderVirtualTreeRows(el.fileTree, rows, renderProjectTreeRow);
  }

  function flattenVisibleProjectTreeRows(tree) {
    const rows = [];
    const visit = (node, depth) => {
      if (!node) {
        return;
      }
      if (node.type === "directory" && depth === -1) {
        (node.children || []).forEach((child) => visit(child, 0));
        return;
      }
      rows.push({ node, depth });
      if (node.type === "directory" && !state.collapsedTreeDirs.has(node.path)) {
        (node.children || []).forEach((child) => visit(child, depth + 1));
      }
    };
    visit(tree, tree && tree.type === "directory" ? -1 : 0);
    return rows;
  }

  function renderProjectTreeRow(row) {
    const node = row && row.node;
    const depth = row ? row.depth : 0;
    if (!node) {
      return "";
    }
    if (node.type === "directory") {
      return renderDirectoryRow(node, depth);
    }
    return renderFileRow(node, depth);
  }

  function renderDirectoryRow(group, depth = 0) {
    const collapsed = state.collapsedTreeDirs.has(group.path);
    const selected = state.selectedTreeKind === "directory" && state.selectedTreePath === group.path;
    return `
      <div class="tree-row tree-folder-row${selected ? " is-selected" : ""}" style="--depth: ${depth}" data-tree-row data-drop-target data-kind="directory" data-path="${escapeAttr(group.path)}">
        <button class="tree-row-main" type="button" data-tree-action="toggle-directory" data-kind="directory" data-path="${escapeAttr(group.path)}">
          <span class="folderIcon" aria-hidden="true">${folderIcon(collapsed ? "closed" : "open")}</span>
          <span class="name" title="${escapeAttr(group.path || group.name)}">${escapeHtml(group.name)}</span>
          <span class="count">${group.fileCount || 0}</span>
        </button>
      </div>
    `;
  }

  function renderProjectTreeNode(node, depth = 0) {
    if (!node) {
      return "";
    }
    if (node.type === "directory") {
      return renderDirectoryGroup(node, depth);
    }
    return renderFileRow(node, depth);
  }

  function renderDirectoryGroup(group, depth = 0) {
    const collapsed = state.collapsedTreeDirs.has(group.path);
    const selected = state.selectedTreeKind === "directory" && state.selectedTreePath === group.path;
    return `
      <div class="tree-group${collapsed ? " is-collapsed" : ""}" data-directory="${escapeAttr(group.path)}">
        <div class="tree-row tree-folder-row${selected ? " is-selected" : ""}" style="--depth: ${depth}" data-tree-row data-drop-target data-kind="directory" data-path="${escapeAttr(group.path)}">
          <button class="tree-row-main" type="button" data-tree-action="toggle-directory" data-kind="directory" data-path="${escapeAttr(group.path)}">
            <span class="folderIcon" aria-hidden="true">${folderIcon(collapsed ? "closed" : "open")}</span>
            <span class="name" title="${escapeAttr(group.path || group.name)}">${escapeHtml(group.name)}</span>
            <span class="count">${group.fileCount || 0}</span>
          </button>
        </div>
        <div class="tree-children">
          ${(group.children || []).map((child) => renderProjectTreeNode(child, depth + 1)).join("")}
        </div>
      </div>
    `;
  }

  function renderFileRow(file, depth = 0) {
    const relativePath = file.relativePath || file.path;
    const selected = state.currentFile === relativePath ||
      (state.selectedTreeKind === "file" && state.selectedTreePath === relativePath);
    return `
      <div class="tree-row tree-file-row${selected ? " is-selected" : ""}" style="--depth: ${depth}" data-tree-row data-draggable-file draggable="true" data-kind="file" data-path="${escapeAttr(relativePath)}">
        <button class="tree-row-main" type="button" data-tree-action="open-file" data-kind="file" data-path="${escapeAttr(relativePath)}">
          <span class="fileIcon ${fileKind(file)}" aria-hidden="true">${fileIcon(file)}</span>
          <span class="name" title="${escapeAttr(relativePath)}">${escapeHtml(file.name)}</span>
          <span class="count">${file.lineCount}</span>
        </button>
      </div>
    `;
  }

  function filterProjectTree(node, filter) {
    if (!node) {
      return null;
    }
    const needle = String(filter || "").trim().toLowerCase();
    if (!needle) {
      return node;
    }
    const matches = String(node.path || node.name || "").toLowerCase().includes(needle);
    if (node.type === "file") {
      return matches ? node : null;
    }
    const children = (node.children || [])
      .map((child) => filterProjectTree(child, needle))
      .filter(Boolean);
    if (matches) {
      return node;
    }
    return children.length > 0 ? { ...node, children } : null;
  }

  function handleTreeAction(event) {
    const action = event.currentTarget.dataset.treeAction;
    const kind = event.currentTarget.dataset.kind;
    const relativePath = event.currentTarget.dataset.path || "";
    closeTreeContextMenu();
    if (action === "toggle-directory") {
      toggleDirectory(relativePath);
      return;
    }
    if (action === "open-file") {
      openProjectTreeFile(relativePath);
      return;
    }
    if (action === "create-file") {
      handleCreateFile(relativePath);
      return;
    }
    if (action === "create-folder") {
      handleCreateFolder(relativePath);
      return;
    }
    if (action === "rename") {
      handleRenameEntry(kind, relativePath);
      return;
    }
    if (action === "delete") {
      handleDeleteEntry(kind, relativePath);
    }
  }

  function handleFileTreeClick(event) {
    const target = event.target && typeof event.target.closest === "function"
      ? event.target.closest("[data-tree-action]")
      : null;
    if (!target || !el.fileTree.contains(target)) {
      return;
    }
    handleTreeAction({ currentTarget: target });
  }

  function handleFileTreeContextMenu(event) {
    if (!state.snapshot) {
      return;
    }
    event.preventDefault();

    const row = event.target.closest("[data-tree-row]");
    const target = row && el.fileTree.contains(row)
      ? {
          kind: row.dataset.kind || "directory",
          path: row.dataset.path || "",
        }
      : {
          kind: "directory",
          path: "",
        };

    state.selectedTreeKind = target.kind;
    state.selectedTreePath = target.path;
    renderFileTree();
    openTreeContextMenu(target.kind, target.path, event.clientX, event.clientY);
  }

  function handleTreeDragStart(event) {
    const row = event.target.closest("[data-draggable-file]");
    if (!row || !el.fileTree.contains(row)) {
      return;
    }
    const relativePath = row.dataset.path || "";
    if (!relativePath) {
      return;
    }

    state.draggedTreeFile = relativePath;
    row.classList.add("is-dragging");
    if (event.dataTransfer) {
      event.dataTransfer.effectAllowed = "move";
      event.dataTransfer.setData("text/plain", relativePath);
    }
    closeTreeContextMenu();
  }

  function handleTreeDragEnd() {
    clearTreeDragState();
  }

  function handleTreeDragOver(event) {
    const target = treeDropTargetFromEvent(event);
    if (!target || !canMoveTreeFileToDirectory(state.draggedTreeFile, target.path)) {
      clearTreeDropTarget();
      return;
    }

    event.preventDefault();
    if (event.dataTransfer) {
      event.dataTransfer.dropEffect = "move";
    }
    markTreeDropTarget(target.path);
  }

  function handleTreeDragLeave(event) {
    const currentTarget = event.target.closest("[data-drop-target]");
    if (!currentTarget || currentTarget.contains(event.relatedTarget)) {
      return;
    }
    clearTreeDropTarget();
  }

  async function handleTreeDrop(event) {
    const target = treeDropTargetFromEvent(event);
    if (!target || !canMoveTreeFileToDirectory(state.draggedTreeFile, target.path)) {
      clearTreeDragState();
      return;
    }

    event.preventDefault();
    const sourcePath = state.draggedTreeFile;
    const targetDirectory = target.path || "";
    clearTreeDragState();
    await handleMoveEntry(sourcePath, targetDirectory);
  }

  function treeDropTargetFromEvent(event) {
    const row = event.target.closest("[data-drop-target]");
    if (!row || !el.fileTree.contains(row)) {
      return null;
    }
    return {
      path: row.dataset.path || "",
    };
  }

  function canMoveTreeFileToDirectory(sourcePath, targetDirectory) {
    if (!sourcePath) {
      return false;
    }
    return normalizeTreeDirectory(parentDirectoryOf(sourcePath)) !== normalizeTreeDirectory(targetDirectory);
  }

  function markTreeDropTarget(relativePath) {
    if (state.treeDropTargetPath === relativePath) {
      return;
    }
    clearTreeDropTarget();
    state.treeDropTargetPath = relativePath;
    const selector = `[data-drop-target][data-path="${cssEscape(relativePath)}"]`;
    const row = el.fileTree.querySelector(selector);
    if (row) {
      row.classList.add("is-drop-target");
    }
  }

  function clearTreeDropTarget() {
    state.treeDropTargetPath = null;
    el.fileTree.querySelectorAll(".is-drop-target").forEach((row) => {
      row.classList.remove("is-drop-target");
    });
  }

  function clearTreeDragState() {
    state.draggedTreeFile = null;
    clearTreeDropTarget();
    el.fileTree.querySelectorAll(".is-dragging").forEach((row) => {
      row.classList.remove("is-dragging");
    });
  }

  function openTreeContextMenu(kind, relativePath, x, y) {
    if (!el.treeContextMenu) {
      return;
    }
    state.treeContext = {
      kind,
      path: relativePath || "",
    };

    el.treeContextMenu.dataset.contextKind = kind;
    el.treeContextMenu.dataset.contextPath = relativePath || "";
    el.treeContextMenu.innerHTML = renderTreeContextMenu(kind, relativePath);
    el.treeContextMenu.hidden = false;
    el.treeContextMenu.style.left = "0px";
    el.treeContextMenu.style.top = "0px";

    const menuRect = el.treeContextMenu.getBoundingClientRect();
    const maxLeft = Math.max(8, window.innerWidth - menuRect.width - 8);
    const maxTop = Math.max(8, window.innerHeight - menuRect.height - 8);
    const left = clamp(x, 8, maxLeft);
    const top = clamp(y, 8, maxTop);
    el.treeContextMenu.style.left = `${left}px`;
    el.treeContextMenu.style.top = `${top}px`;

    const firstAction = el.treeContextMenu.querySelector("[data-context-action]");
    if (firstAction) {
      firstAction.focus();
    }
  }

  function renderTreeContextMenu(kind, relativePath) {
    const label = relativePath || "项目根目录";
    const items = [
      `<div class="context-menu-label" title="${escapeAttr(label)}">${escapeHtml(label)}</div>`,
    ];

    if (kind === "directory") {
      items.push(contextMenuItem("create-file", "新建文件"));
      items.push(contextMenuItem("create-folder", "新建目录"));
      if (relativePath) {
        items.push(contextMenuSeparator());
        items.push(contextMenuItem("rename", "重命名"));
        items.push(contextMenuItem("delete", "删除", "danger"));
      }
    } else {
      items.push(contextMenuItem("open-file", "打开文件"));
      items.push(contextMenuSeparator());
      items.push(contextMenuItem("rename", "重命名"));
      items.push(contextMenuItem("delete", "删除", "danger"));
    }

    return items.join("");
  }

  function contextMenuItem(action, label, tone = "") {
    const toneClass = tone ? ` ${tone}` : "";
    return `<button class="context-menu-item${toneClass}" type="button" role="menuitem" data-context-action="${escapeAttr(action)}">${escapeHtml(label)}</button>`;
  }

  function contextMenuSeparator() {
    return `<div class="context-menu-separator" role="separator"></div>`;
  }

  async function handleTreeContextMenuClick(event) {
    const button = event.target.closest("[data-context-action]");
    if (!button || !el.treeContextMenu.contains(button)) {
      return;
    }
    event.preventDefault();
    event.stopPropagation();

    const action = button.dataset.contextAction;
    const context = readTreeContextMenuContext();
    if (!context) {
      closeTreeContextMenu();
      return;
    }
    closeTreeContextMenu();

    if (action === "open-file") {
      await openProjectTreeFile(context.path);
      return;
    }
    if (action === "create-file") {
      await handleCreateFile(context.path);
      return;
    }
    if (action === "create-folder") {
      await handleCreateFolder(context.path);
      return;
    }
    if (action === "rename") {
      await handleRenameEntry(context.kind, context.path);
      return;
    }
    if (action === "delete") {
      await handleDeleteEntry(context.kind, context.path);
    }
  }

  function readTreeContextMenuContext() {
    if (el.treeContextMenu.dataset.contextKind) {
      return {
        kind: el.treeContextMenu.dataset.contextKind,
        path: el.treeContextMenu.dataset.contextPath || "",
      };
    }
    return state.treeContext ? { ...state.treeContext } : null;
  }

  function closeTreeContextMenu() {
    state.treeContext = null;
    if (!el.treeContextMenu) {
      return;
    }
    el.treeContextMenu.hidden = true;
    el.treeContextMenu.innerHTML = "";
    delete el.treeContextMenu.dataset.contextKind;
    delete el.treeContextMenu.dataset.contextPath;
  }

  function toggleDirectory(relativePath) {
    state.selectedTreeKind = "directory";
    state.selectedTreePath = relativePath;
    if (state.collapsedTreeDirs.has(relativePath)) {
      state.collapsedTreeDirs.delete(relativePath);
    } else {
      state.collapsedTreeDirs.add(relativePath);
    }
    renderFileTree();
  }

  async function openProjectTreeFile(relativePath) {
    state.selectedTreeKind = "file";
    state.selectedTreePath = relativePath;
    if (
      state.dirty &&
      !window.confirm("当前文件尚未保存，是否继续打开其他文件？")
    ) {
      renderFileTree();
      return;
    }
    await selectFile(relativePath);
  }

  async function handleCreateFile(directory = null) {
    await createTreeEntry("file", directory);
  }

  async function handleCreateFolder(directory = null) {
    await createTreeEntry("directory", directory);
  }

  function requestEntryName({ title, label, defaultValue = "" }) {
    if (state.entryDialogResolve) {
      closeEntryDialog(null);
    }

    return new Promise((resolve) => {
      state.entryDialogResolve = resolve;
      state.entryDialogPreviousFocus =
        document.activeElement && typeof document.activeElement.focus === "function"
          ? document.activeElement
          : null;
      el.entryDialogTitle.textContent = title;
      el.entryDialogLabel.textContent = label;
      el.entryDialogInput.value = defaultValue;
      el.entryDialogError.hidden = true;
      el.entryDialogError.textContent = "";
      el.entryDialog.hidden = false;
      requestAnimationFrame(() => {
        el.entryDialogInput.focus();
        el.entryDialogInput.select();
      });
    });
  }

  function handleEntryDialogSubmit(event) {
    event.preventDefault();
    const value = el.entryDialogInput.value.trim();
    if (!value) {
      showEntryDialogError("名称不能为空");
      return;
    }
    closeEntryDialog(value);
  }

  function showEntryDialogError(message) {
    el.entryDialogError.textContent = message;
    el.entryDialogError.hidden = false;
    el.entryDialogInput.focus();
  }

  function closeEntryDialog(value) {
    if (!el.entryDialog) {
      return;
    }
    const resolve = state.entryDialogResolve;
    const previousFocus = state.entryDialogPreviousFocus;
    state.entryDialogResolve = null;
    state.entryDialogPreviousFocus = null;
    el.entryDialog.hidden = true;
    el.entryDialogInput.value = "";
    el.entryDialogError.hidden = true;
    el.entryDialogError.textContent = "";
    if (resolve) {
      resolve(value);
    }
    if (previousFocus && document.contains(previousFocus)) {
      previousFocus.focus();
    }
  }

  async function createTreeEntry(kind, directory = null) {
    if (!state.snapshot) {
      appendLog("warn", "请先打开一个项目");
      return;
    }
    const targetDirectory = normalizeTreeDirectory(
      directory === null ? selectedTargetDirectory() : directory,
    );
    const defaultName = kind === "directory" ? "new_folder" : "new_file.dsl";
    const name = await requestEntryName({
      title: kind === "directory" ? "新建目录" : "新建文件",
      label: kind === "directory" ? "目录名称" : "文件名称",
      defaultValue: defaultName,
    });
    if (!name) {
      return;
    }
    const relativePath = joinRelativePath(targetDirectory, name);
    try {
      const result = await api.createEntry(state.snapshot.project.rootPath, {
        kind,
        relativePath,
        content: kind === "file" ? "" : undefined,
      });
      if (kind === "directory") {
        state.selectedTreeKind = "directory";
        state.selectedTreePath = result.relativePath;
        state.collapsedTreeDirs.delete(result.relativePath);
      } else {
        state.selectedTreeKind = "file";
        state.selectedTreePath = result.relativePath;
      }
      await refreshProject({
        logMessage: `${kind === "directory" ? "Created folder" : "Created file"} ${result.relativePath}`,
        preferredFile: kind === "file" ? result.relativePath : state.currentFile,
      });
    } catch (error) {
      appendLog("error", errorMessage(error));
    }
  }

  async function handleRenameEntry(kind, relativePath) {
    if (!state.snapshot || !relativePath) {
      return;
    }
    if (!confirmDirtyTreeMutation(kind, relativePath)) {
      return;
    }
    const currentName = fileNameFromPath(relativePath);
    const newName = await requestEntryName({
      title: "重命名",
      label: "新名称",
      defaultValue: currentName,
    });
    if (!newName || newName === currentName) {
      return;
    }
    try {
      const result = await api.renameEntry(state.snapshot.project.rootPath, {
        relativePath,
        newName,
      });
      const preferredFile = remapPathAfterRename(relativePath, result.relativePath, state.currentFile);
      state.selectedTreeKind = kind;
      state.selectedTreePath = result.relativePath;
      await refreshProject({
        logMessage: `Renamed ${relativePath} -> ${result.relativePath}`,
        preferredFile,
      });
    } catch (error) {
      appendLog("error", errorMessage(error));
    }
  }

  async function handleMoveEntry(relativePath, targetDirectory) {
    if (!state.snapshot || !relativePath) {
      return;
    }
    const normalizedTargetDirectory = normalizeTreeDirectory(targetDirectory);
    if (!canMoveTreeFileToDirectory(relativePath, normalizedTargetDirectory)) {
      appendLog("info", `File already in ${normalizedTargetDirectory || "project root"}: ${relativePath}`);
      return;
    }
    if (!confirmDirtyTreeMutation("file", relativePath)) {
      return;
    }

    try {
      const result = await api.moveEntry(state.snapshot.project.rootPath, {
        relativePath,
        targetDirectory: normalizedTargetDirectory,
      });
      state.selectedTreeKind = "file";
      state.selectedTreePath = result.relativePath;
      state.collapsedTreeDirs.delete(normalizedTargetDirectory);
      await refreshProject({
        logMessage: `Moved ${relativePath} -> ${result.relativePath}`,
        preferredFile: state.currentFile === relativePath ? result.relativePath : state.currentFile,
      });
    } catch (error) {
      appendLog("error", errorMessage(error));
    }
  }

  async function handleDeleteEntry(kind, relativePath) {
    if (!state.snapshot || !relativePath) {
      return;
    }
    if (!confirmDirtyTreeMutation(kind, relativePath)) {
      return;
    }
    const label = kind === "directory" ? `目录 ${relativePath} 及其内容` : `文件 ${relativePath}`;
    if (!window.confirm(`确认删除${label}？`)) {
      return;
    }
    try {
      const affectsCurrent = pathAffectsCurrentFile(kind, relativePath);
      const result = await api.deleteEntry(state.snapshot.project.rootPath, {
        relativePath,
        recursive: kind === "directory",
      });
      state.selectedTreeKind = "directory";
      state.selectedTreePath = parentDirectoryOf(relativePath);
      await refreshProject({
        logMessage: `Deleted ${result.relativePath}`,
        preferredFile: affectsCurrent ? null : state.currentFile,
      });
    } catch (error) {
      appendLog("error", errorMessage(error));
    }
  }

  function selectedTargetDirectory() {
    if (state.selectedTreeKind === "directory") {
      return state.selectedTreePath || "";
    }
    if (state.selectedTreeKind === "file" && state.selectedTreePath) {
      return parentDirectoryOf(state.selectedTreePath);
    }
    if (state.currentFile) {
      return parentDirectoryOf(state.currentFile);
    }
    return "";
  }

  function confirmDirtyTreeMutation(kind, relativePath) {
    if (!state.dirty || !pathAffectsCurrentFile(kind, relativePath)) {
      return true;
    }
    return window.confirm("当前文件尚未保存，继续操作会丢失未保存内容，是否继续？");
  }

  function pathAffectsCurrentFile(kind, relativePath) {
    if (!state.currentFile) {
      return false;
    }
    if (kind === "file") {
      return state.currentFile === relativePath;
    }
    return state.currentFile === relativePath || state.currentFile.startsWith(`${relativePath}/`);
  }

  function remapPathAfterRename(oldPath, newPath, currentPath) {
    if (!currentPath) {
      return currentPath;
    }
    if (currentPath === oldPath) {
      return newPath;
    }
    if (currentPath.startsWith(`${oldPath}/`)) {
      return `${newPath}${currentPath.slice(oldPath.length)}`;
    }
    return currentPath;
  }

  function parentDirectoryOf(relativePath) {
    const parts = String(relativePath || "").split("/").filter(Boolean);
    parts.pop();
    return parts.join("/");
  }

  function normalizeTreeDirectory(relativePath) {
    return String(relativePath || "").replace(/\\/g, "/").replace(/^\/+|\/+$/g, "");
  }

  function joinRelativePath(directory, name) {
    return [normalizeTreeDirectory(directory), String(name || "").trim()]
      .filter(Boolean)
      .join("/");
  }

  function setAllTreeGroupsCollapsed(collapsed) {
    if (!state.snapshot || !state.snapshot.tree) {
      return;
    }
    if (collapsed) {
      collectProjectDirectoryPaths(state.snapshot.tree)
        .filter(Boolean)
        .forEach((directory) => state.collapsedTreeDirs.add(directory));
    } else {
      state.collapsedTreeDirs.clear();
    }
    renderFileTree();
  }

  function collectProjectDirectoryPaths(node) {
    if (!node || node.type !== "directory") {
      return [];
    }
    return [
      node.path,
      ...(node.children || []).flatMap(collectProjectDirectoryPaths),
    ];
  }

  // Default project-tree state: expand only the project root, so the first
  // level of children stays visible while every deeper directory starts
  // collapsed. This keeps the per-interaction flatten cost bounded for large
  // projects while still showing what users open a project to find.
  function collapseTreeDirsBelowRoot() {
    state.collapsedTreeDirs.clear();
    if (!state.snapshot || !state.snapshot.tree) {
      return;
    }
    const root = state.snapshot.tree;
    if (!root || root.type !== "directory") {
      return;
    }
    // Root's own children are rendered because the root is not in the collapsed
    // set; we only need to fold the children that are themselves directories.
    (root.children || []).forEach((child) => {
      collectProjectDirectoryPaths(child)
        .filter(Boolean)
        .forEach((directory) => state.collapsedTreeDirs.add(directory));
    });
  }

  return {
    closeEntryDialog,
    closeTreeContextMenu,
    clearTreeDragState,
    collapseTreeDirsBelowRoot,
    handleEntryDialogSubmit,
    handleFileTreeClick,
    handleFileTreeContextMenu,
    handleProjectTreeScroll,
    handleTreeContextMenuClick,
    handleTreeDragEnd,
    handleTreeDragLeave,
    handleTreeDragOver,
    handleTreeDragStart,
    handleTreeDrop,
    renderFileTree,
    scheduleFileTreeRender,
    setAllTreeGroupsCollapsed,
  };
}
