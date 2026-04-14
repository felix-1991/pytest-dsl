# CI/CD集成

::: warning 状态说明
目前没有额外的“官方” CI/CD 集成插件，按常规 pytest 流程即可运行 pytest-dsl。以下示例仅作为参考模版，可根据团队的流水线工具自由调整。
:::

pytest-dsl 依赖 pytest 运行，能以常规 pytest 方式接入各类 CI/CD 平台。下面给出常见平台的示例配置，按需裁剪使用。

`pytest-dsl` 独立 CLI 目前只支持基础执行参数，例如 `path`、`--yaml-vars`、`--yaml-vars-dir`。
如果流水线需要 `-v`、`--junit-xml`、`--html` 等 pytest 参数，请改走 pytest 集成入口。

## GitHub Actions

### 基本工作流

创建 `.github/workflows/test.yml` 文件：

```yaml
name: 自动化测试

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.9, '3.10', '3.11', '3.12']

    steps:
    - name: 检出代码
      uses: actions/checkout@v3

    - name: 设置Python环境
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}

    - name: 安装依赖
      run: |
        python -m pip install --upgrade pip
        pip install pytest-dsl pytest-html allure-pytest

    - name: 运行DSL测试
      run: |
        pytest-dsl tests/

    - name: 运行pytest集成测试
      run: |
        pytest tests/ --html=report.html --self-contained-html

    - name: 上传测试报告
      uses: actions/upload-artifact@v3
      if: always()
      with:
        name: test-reports-python-${{ matrix.python-version }}
        path: |
          report.html
          allure-results/
```

### 带环境变量的工作流

```yaml
name: 多环境测试

on:
  push:
    branches: [ main ]
  schedule:
    - cron: '0 2 * * *'  # 每天凌晨2点执行

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        environment: [dev, staging, prod]

    env:
      TEST_ENV: ${{ matrix.environment }}
      API_BASE_URL: ${{ secrets.API_BASE_URL }}
      AUTH_TOKEN: ${{ secrets.AUTH_TOKEN }}

    steps:
    - uses: actions/checkout@v3

    - name: 设置Python环境
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'

    - name: 安装依赖
      run: |
        pip install -r requirements.txt

    - name: 准备测试配置
      run: |
        envsubst < config/template.yaml > config/${{ matrix.environment }}.yaml

    - name: 运行环境测试
      run: |
        pytest-dsl tests/ --yaml-vars config/${{ matrix.environment }}.yaml

    - name: 生成Allure报告
      if: always()
      run: |
        allure generate allure-results -o allure-report --clean

    - name: 部署测试报告
      if: matrix.environment == 'prod'
      uses: peaceiris/actions-gh-pages@v3
      with:
        github_token: ${{ secrets.GITHUB_TOKEN }}
        publish_dir: ./allure-report
```

### 并行测试执行

```yaml
name: 并行测试

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        test-group:
          - "基础功能"
          - "API测试"
          - "认证测试"
          - "集成测试"

    steps:
    - uses: actions/checkout@v3

    - name: 设置Python环境
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'

    - name: 安装依赖
      run: |
        pip install pytest-dsl

    - name: 运行测试组
      run: |
        case "${{ matrix.test-group }}" in
          "基础功能")
            pytest-dsl tests/basic/
            ;;
          "API测试")
            pytest-dsl tests/api/
            ;;
          "认证测试")
            pytest-dsl tests/auth/
            ;;
          "集成测试")
            pytest-dsl tests/integration/
            ;;
        esac

    - name: 上传测试结果
      uses: actions/upload-artifact@v3
      if: always()
      with:
        name: results-${{ matrix.test-group }}
        path: test-results/
```

## GitLab CI/CD

### 基本配置

创建 `.gitlab-ci.yml` 文件：

```yaml
stages:
  - test
  - report
  - deploy

variables:
  PIP_CACHE_DIR: "$CI_PROJECT_DIR/.cache/pip"

cache:
  paths:
    - .cache/pip/

before_script:
  - python -m pip install --upgrade pip
  - pip install pytest-dsl pytest-html

test:
  stage: test
  image: python:3.10
  script:
    - pytest-dsl tests/
  artifacts:
    when: always
    paths:
      - test-results/
    expire_in: 1 week

test_multiple_versions:
  stage: test
  parallel:
    matrix:
      - PYTHON_VERSION: ["3.9", "3.10", "3.11", "3.12"]
  image: python:${PYTHON_VERSION}
  script:
    - pip install pytest-dsl
    - pytest-dsl tests/

generate_reports:
  stage: report
  image: python:3.10
  dependencies:
    - test
  script:
    - pip install allure-commandline
    - allure generate test-results/allure-results -o public
  artifacts:
    paths:
      - public
  only:
    - main

pages:
  stage: deploy
  dependencies:
    - generate_reports
  script:
    - echo "Deploying test reports to GitLab Pages"
  artifacts:
    paths:
      - public
  only:
    - main
```

## Jenkins

### Jenkinsfile (声明式)

```groovy
pipeline {
    agent any
    
    parameters {
        choice(
            name: 'ENVIRONMENT',
            choices: ['dev', 'staging', 'prod'],
            description: '选择测试环境'
        )
        booleanParam(
            name: 'RUN_PERFORMANCE_TESTS',
            defaultValue: false,
            description: '是否运行性能测试'
        )
    }
    
    environment {
        PYTHONPATH = "${WORKSPACE}"
        TEST_ENV = "${params.ENVIRONMENT}"
    }
    
    stages {
        stage('准备环境') {
            steps {
                sh '''
                    python -m venv venv
                    . venv/bin/activate
                    pip install --upgrade pip
                    pip install pytest-dsl pytest-html allure-pytest
                '''
            }
        }
        
        stage('运行基础测试') {
            steps {
                sh '''
                    . venv/bin/activate
                    pytest-dsl tests/basic/
                '''
            }
            post {
                always {
                    echo '如需 JUnit，请改走 pytest 集成入口'
                }
            }
        }
        
        stage('运行API测试') {
            parallel {
                stage('API功能测试') {
                    steps {
                        sh '''
                            . venv/bin/activate
                            pytest-dsl tests/api/ --yaml-vars config/${TEST_ENV}.yaml
                        '''
                    }
                }
                stage('API性能测试') {
                    when {
                        params.RUN_PERFORMANCE_TESTS == true
                    }
                    steps {
                        sh '''
                            . venv/bin/activate
                            pytest-dsl tests/performance/ --yaml-vars config/${TEST_ENV}.yaml
                        '''
                    }
                }
            }
        }
        
        stage('生成报告') {
            steps {
                sh '''
                    . venv/bin/activate
                    allure generate allure-results -o allure-report --clean
                '''
                publishHTML([
                    allowMissing: false,
                    alwaysLinkToLastBuild: true,
                    keepAll: true,
                    reportDir: 'allure-report',
                    reportFiles: 'index.html',
                    reportName: 'Allure Report'
                ])
            }
        }
    }
    
    post {
        always {
            archiveArtifacts artifacts: 'allure-report/**', fingerprint: true
            cleanWs()
        }
        failure {
            emailext (
                subject: "测试失败: ${env.JOB_NAME} - ${env.BUILD_NUMBER}",
                body: "测试执行失败，请检查: ${env.BUILD_URL}",
                to: "${env.CHANGE_AUTHOR_EMAIL}"
            )
        }
    }
}
```

### Jenkinsfile (脚本式)

```groovy
node {
    def testResults = [:]
    
    try {
        stage('检出代码') {
            checkout scm
        }
        
        stage('准备环境') {
            sh '''
                python -m venv venv
                . venv/bin/activate
                pip install pytest-dsl
            '''
        }
        
        stage('并行测试') {
            parallel(
                '基础测试': {
                    testResults['basic'] = sh(
                        script: '. venv/bin/activate && pytest-dsl tests/basic/',
                        returnStatus: true
                    )
                },
                'API测试': {
                    testResults['api'] = sh(
                        script: '. venv/bin/activate && pytest-dsl tests/api/',
                        returnStatus: true
                    )
                },
                '集成测试': {
                    testResults['integration'] = sh(
                        script: '. venv/bin/activate && pytest-dsl tests/integration/',
                        returnStatus: true
                    )
                }
            )
        }
        
        stage('分析结果') {
            def failedTests = testResults.findAll { k, v -> v != 0 }
            if (failedTests) {
                error("以下测试失败: ${failedTests.keySet().join(', ')}")
            }
        }
        
    } catch (Exception e) {
        currentBuild.result = 'FAILURE'
        throw e
    } finally {
        stage('清理') {
            cleanWs()
        }
    }
}
```

## Azure DevOps

### Azure Pipelines YAML

```yaml
trigger:
  branches:
    include:
    - main
    - develop

pr:
  branches:
    include:
    - main

pool:
  vmImage: 'ubuntu-latest'

strategy:
  matrix:
    Python39:
      python.version: '3.9'
    Python310:
      python.version: '3.10'
    Python311:
      python.version: '3.11'

variables:
  pythonVersion: $(python.version)

steps:
- task: UsePythonVersion@0
  inputs:
    versionSpec: '$(pythonVersion)'
  displayName: '使用Python $(pythonVersion)'

- script: |
    python -m pip install --upgrade pip
    pip install pytest-dsl pytest-html
  displayName: '安装依赖'

- script: |
    pytest-dsl tests/
  displayName: '运行DSL测试'

- task: PublishTestResults@2
  condition: always()
  inputs:
    testResultsFiles: '**/TEST-*.xml'
    testRunTitle: 'DSL Tests - Python $(pythonVersion)'

- task: PublishHtmlReport@1
  condition: always()
  inputs:
    reportDir: '.'
    tabName: 'DSL Test Report'
```

### 多阶段流水线

```yaml
stages:
- stage: Test
  displayName: '测试阶段'
  jobs:
  - job: UnitTests
    displayName: '单元测试'
    pool:
      vmImage: 'ubuntu-latest'
    steps:
    - script: |
        pip install pytest-dsl
        pytest-dsl tests/unit/
      displayName: '运行单元测试'

  - job: IntegrationTests
    displayName: '集成测试'
    dependsOn: UnitTests
    pool:
      vmImage: 'ubuntu-latest'
    steps:
    - script: |
        pip install pytest-dsl
        pytest-dsl tests/integration/
      displayName: '运行集成测试'

- stage: Deploy
  displayName: '部署阶段'
  dependsOn: Test
  condition: and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/main'))
  jobs:
  - deployment: DeployToStaging
    displayName: '部署到预发布环境'
    environment: 'staging'
    strategy:
      runOnce:
        deploy:
          steps:
          - script: |
              pytest-dsl tests/smoke/ --yaml-vars config/staging.yaml
            displayName: '冒烟测试'
```

## Docker 集成

### Dockerfile 示例

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制需求文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制测试文件
COPY tests/ ./tests/
COPY config/ ./config/

# 设置环境变量
ENV PYTHONPATH=/app
ENV TEST_ENV=docker

# 运行测试
CMD ["pytest-dsl", "tests/"]
```

### docker-compose.yml

```yaml
version: '3.9'

services:
  test-runner:
    build: .
    environment:
      - TEST_ENV=docker
      - API_BASE_URL=http://api:8000
    depends_on:
      - api
    volumes:
      - ./test-results:/app/test-results
    command: pytest-dsl tests/

  api:
    image: nginx:alpine
    ports:
      - "8000:80"
    volumes:
      - ./mock-api:/usr/share/nginx/html

  allure:
    image: frankescobar/allure-docker-service
    ports:
      - "5050:5050"
    environment:
      CHECK_RESULTS_EVERY_SECONDS: 3
    volumes:
      - ./test-results/allure-results:/app/allure-results
```

## 监控和通知

### Slack 集成

```python
# slack_notifier.py
import requests
import json
import subprocess
import time

def send_slack_notification(webhook_url, message):
    """发送Slack通知"""
    payload = {
        "text": message,
        "username": "DSL Test Bot",
        "icon_emoji": ":robot_face:"
    }
    
    response = requests.post(webhook_url, json=payload)
    return response.status_code == 200

def run_tests_with_notification(test_files, slack_webhook):
    """运行测试并发送通知"""
    results = []
    
    for test_file in test_files:
        start = time.time()
        completed = subprocess.run(
            ["pytest-dsl", test_file],
            capture_output=True,
            text=True,
        )
        results.append({
            "file": test_file,
            "success": completed.returncode == 0,
            "duration": time.time() - start
        })
    
    # 生成报告
    total = len(results)
    passed = sum(1 for r in results if r["success"])
    failed = total - passed
    
    # 发送通知
    if failed > 0:
        message = f"🔴 DSL测试执行完成\n总数: {total}, 通过: {passed}, 失败: {failed}"
        emoji = ":x:"
    else:
        message = f"✅ DSL测试全部通过\n总数: {total}, 通过: {passed}"
        emoji = ":white_check_mark:"
    
    send_slack_notification(slack_webhook, f"{emoji} {message}")

# 在CI中使用
if __name__ == "__main__":
    import os
    
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    test_files = ["tests/api.dsl", "tests/auth.dsl"]
    
    run_tests_with_notification(test_files, webhook_url)
```

### 邮件通知

```python
# email_notifier.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class EmailNotifier:
    def __init__(self, smtp_server, smtp_port, username, password):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
    
    def send_test_report(self, recipients, test_results):
        """发送测试报告邮件"""
        msg = MIMEMultipart()
        msg['From'] = self.username
        msg['To'] = ', '.join(recipients)
        msg['Subject'] = "DSL自动化测试报告"
        
        # 生成邮件内容
        total = len(test_results)
        passed = sum(1 for r in test_results if r["success"])
        failed = total - passed
        
        body = f"""
        DSL自动化测试执行完成
        
        执行摘要：
        - 总测试数: {total}
        - 通过: {passed}
        - 失败: {failed}
        - 成功率: {passed/total:.1%}
        
        详细结果：
        """
        
        for result in test_results:
            status = "✅" if result["success"] else "❌"
            body += f"\n{status} {result['file']} - {result['duration']:.2f}s"
        
        msg.attach(MIMEText(body, 'plain'))
        
        # 发送邮件
        try:
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.username, self.password)
            text = msg.as_string()
            server.sendmail(self.username, recipients, text)
            server.quit()
            print("邮件发送成功")
        except Exception as e:
            print(f"邮件发送失败: {e}")
```

## 最佳实践

### 1. 测试隔离

确保测试之间互不影响：

```yaml
# 每次测试使用独立的数据库
services:
  test-db:
    image: postgres:13
    environment:
      POSTGRES_DB: test_${CI_JOB_ID}
      POSTGRES_USER: test
      POSTGRES_PASSWORD: test
```

### 2. 缓存优化

利用依赖缓存加速构建：

```yaml
# GitHub Actions
- name: 缓存Python依赖
  uses: actions/cache@v3
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}

# GitLab CI
cache:
  key: ${CI_COMMIT_REF_SLUG}
  paths:
    - .cache/pip/
    - venv/
```

### 3. 条件执行

根据变更内容决定是否运行测试：

```yaml
# 只在相关文件变更时运行
on:
  push:
    paths:
      - 'tests/**'
      - 'src/**'
      - 'requirements.txt'
```

### 4. 错误处理

设置合理的超时和重试机制：

```yaml
- name: 运行测试
  timeout-minutes: 30
  run: |
    for i in {1..3}; do
      pytest-dsl tests/ && break
      echo "重试第 $i 次..."
      sleep 10
    done
```

通过这些CI/CD集成实践，您可以构建一个强大、可靠的自动化测试流水线，确保代码质量并加速交付周期。 
