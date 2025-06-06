# pytest-dsl 文档

这是pytest-dsl的官方文档，使用VitePress构建。

## 文档结构

```
docs/
├── .vitepress/
│   └── config.js          # VitePress配置文件
├── guide/                 # 教程指南
│   ├── index.md          # 教程首页
│   ├── introduction.md   # 项目介绍
│   ├── getting-started.md # 快速开始
│   ├── dsl-syntax.md     # DSL语法基础
│   ├── http-testing.md   # HTTP API测试
│   └── remote-keywords.md # 远程关键字
├── reference/             # API参考
│   └── index.md          # 参考首页
├── examples/              # 示例库
│   ├── index.md          # 示例首页
│   └── hello-world.md    # Hello World示例
├── index.md              # 文档首页
└── README.md             # 本文件
```

## 本地开发

### 安装依赖

```bash
npm install
```

### 启动开发服务器

```bash
npm run docs:dev
```

### 构建文档

```bash
npm run docs:build
```

### 预览构建结果

```bash
npm run docs:preview
```

## 文档特点

### 🎯 用户友好

- **渐进式学习路径** - 从基础到高级的完整学习路径
- **丰富的示例** - 每个功能都有实际可运行的示例
- **中文文档** - 完整的中文技术文档
- **搜索功能** - 支持全文搜索

### 📚 内容完整

- **入门指南** - 快速上手和基础概念
- **详细教程** - 深入的功能讲解和最佳实践
- **API参考** - 完整的技术参考文档
- **示例库** - 丰富的实际应用示例

### 🔧 技术特性

- **VitePress驱动** - 快速、现代的文档框架
- **响应式设计** - 支持桌面和移动设备
- **语法高亮** - 代码示例支持语法高亮
- **导航友好** - 清晰的导航结构和面包屑

## 文档维护

### 添加新页面

1. 在相应目录下创建markdown文件
2. 在`.vitepress/config.js`中添加导航配置
3. 确保内部链接正确

### 更新现有页面

1. 直接编辑对应的markdown文件
2. 确保示例代码可以正常运行
3. 更新相关的交叉引用

### 文档规范

- **文件命名** - 使用kebab-case命名（如`getting-started.md`）
- **标题层级** - 合理使用H1-H6标题层级
- **代码示例** - 确保所有代码示例可以运行
- **链接检查** - 定期检查内部和外部链接的有效性

## 贡献指南

### 内容贡献

1. Fork项目仓库
2. 创建功能分支
3. 编写或更新文档
4. 提交Pull Request

### 质量标准

- **准确性** - 确保技术信息准确无误
- **完整性** - 提供完整的使用说明和示例
- **清晰性** - 使用简洁明了的语言
- **一致性** - 保持文档风格和格式一致

### 审核流程

1. 技术审核 - 验证技术内容的准确性
2. 语言审核 - 检查语言表达和格式规范
3. 测试验证 - 确保示例代码可以正常运行
4. 最终审核 - 整体质量和用户体验检查

## 部署

文档通过GitHub Pages自动部署，每次推送到main分支时会自动触发构建和部署。

### 部署配置

- **构建命令** - `npm run docs:build`
- **输出目录** - `docs/.vitepress/dist`
- **部署分支** - `gh-pages`

## 反馈和支持

- **问题报告** - [GitHub Issues](https://github.com/felix-1991/pytest-dsl/issues)
- **功能建议** - [GitHub Discussions](https://github.com/felix-1991/pytest-dsl/discussions)
- **文档改进** - 通过Pull Request提交

---

感谢您对pytest-dsl文档的贡献！ 