import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'pytest-dsl',
  description: '强大的关键字驱动测试自动化框架',
  lang: 'zh-CN',
  
  themeConfig: {
    logo: '/logo-simple.svg',
    
    nav: [
      { text: '首页', link: '/' },
      { text: '快速开始', link: '/guide/getting-started' },
      { text: 'GitHub', link: 'https://github.com/felix-1991/pytest-dsl' }
    ],

    sidebar: {
      '/guide/': [
        {
          text: '入门指南',
          items: [
            { text: '什么是pytest-dsl', link: '/guide/introduction' },
            { text: '快速开始', link: '/guide/getting-started' },
            { text: '安装配置', link: '/guide/installation' },
            { text: '第一个测试', link: '/guide/first-test' }
          ]
        },
        {
          text: '基础教程',
          items: [
            { text: 'DSL语法基础', link: '/guide/dsl-syntax' },
            { text: '变量和数据类型', link: '/guide/variables' },
            { text: '流程控制', link: '/guide/control-flow' },
            { text: '内置关键字', link: '/guide/builtin-keywords' }
          ]
        },
        {
          text: '进阶功能',
          items: [
            { text: '自定义关键字', link: '/guide/custom-keywords' },
            { text: '资源文件', link: '/guide/resource-files' },
            { text: 'HTTP API测试', link: '/guide/http-testing' },
            { text: 'Web UI测试', link: '/guide/ui-testing' },
            { text: '数据驱动测试', link: '/guide/data-driven' },
            { text: '环境配置管理', link: '/guide/configuration' }
          ]
        },
        {
          text: '开发工具',
          items: [
            { text: 'VS Code扩展', link: '/guide/vscode-extension' }
          ]
        },
        {
          text: '集成与工具',
          items: [
            { text: 'pytest集成', link: '/guide/pytest-integration' },
            { text: '测试报告', link: '/guide/reporting' },
            { text: 'CI/CD集成', link: '/guide/cicd' },
            { text: '命令行工具', link: '/guide/cli-tools' },
            { text: '最佳实践', link: '/guide/best-practices' }
          ]
        },
        {
          text: '高级特性',
          items: [
            { text: '远程关键字', link: '/guide/remote-keywords' },
            { text: '远程服务器Hook', link: '/guide/remote-hooks' }
          ]
        }
      ],
      
    },
    socialLinks: [
      { icon: 'github', link: 'https://github.com/felix-1991/pytest-dsl' }
    ],

    footer: {
      message: 'Released under the MIT License.',
      copyright: 'Copyright © 2024 pytest-dsl'
    },

    search: {
      provider: 'local'
    },

    editLink: {
      pattern: 'https://github.com/felix-1991/pytest-dsl/edit/main/docs/:path',
      text: '在 GitHub 上编辑此页'
    },

    lastUpdated: {
      text: '最后更新',
      formatOptions: {
        dateStyle: 'short',
        timeStyle: 'medium'
      }
    }
  },

  markdown: {
    lineNumbers: true,
    config: (md) => {
      // 添加自定义markdown插件
    }
  }
}) 