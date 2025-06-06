# 测试报告

pytest-dsl 支持多种测试报告格式，帮助您更好地了解测试执行情况、分析测试结果，并生成专业的测试报告。

## 内置报告功能

### 控制台输出

默认情况下，pytest-dsl 会在控制台输出测试执行信息：

```bash
# 详细模式
pytest-dsl hello.dsl -v

# 静默模式
pytest-dsl hello.dsl -q

# 显示执行步骤
pytest-dsl hello.dsl --show-steps
```

### 执行结果对象

通过编程方式运行时，可以获取详细的执行结果：

```python
from pytest_dsl import run_dsl_file

result = run_dsl_file("hello.dsl")

print(f"执行成功: {result.success}")
print(f"执行时间: {result.duration}")
print(f"执行步骤数: {result.step_count}")
print(f"错误信息: {result.error_message}")
```

## HTML 报告

### 使用 pytest-html

安装 pytest-html 插件：

```bash
pip install pytest-html
```

生成 HTML 报告：

```python
# test_reports.py
import pytest
from pytest_dsl import run_dsl_file

def test_api_suite():
    """API测试套件"""
    result = run_dsl_file("api_basic.dsl")
    assert result.success

def test_auth_suite():
    """认证测试套件"""
    result = run_dsl_file("auth_test.dsl")
    assert result.success
```

运行并生成报告：

```bash
pytest test_reports.py --html=report.html --self-contained-html
```

### 自定义 HTML 报告

创建自定义报告生成器：

```python
# report_generator.py
from pytest_dsl import run_dsl_file
import datetime
import json

class DSLReportGenerator:
    def __init__(self):
        self.results = []
        
    def run_test_suite(self, dsl_files):
        """运行测试套件并收集结果"""
        for dsl_file in dsl_files:
            result = run_dsl_file(dsl_file)
            self.results.append({
                "file": dsl_file,
                "success": result.success,
                "duration": result.duration,
                "error": result.error_message,
                "timestamp": datetime.datetime.now().isoformat()
            })
    
    def generate_html_report(self, output_file="dsl_report.html"):
        """生成HTML报告"""
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>DSL测试报告</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .summary { background: #f0f0f0; padding: 10px; margin-bottom: 20px; }
                .success { color: green; }
                .failed { color: red; }
                table { border-collapse: collapse; width: 100%; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #f2f2f2; }
            </style>
        </head>
        <body>
            <h1>DSL测试报告</h1>
            <div class="summary">
                <h2>执行摘要</h2>
                <p>总测试数: {total}</p>
                <p class="success">通过: {passed}</p>
                <p class="failed">失败: {failed}</p>
                <p>成功率: {success_rate:.1%}</p>
            </div>
            
            <h2>详细结果</h2>
            <table>
                <tr>
                    <th>测试文件</th>
                    <th>状态</th>
                    <th>执行时间</th>
                    <th>错误信息</th>
                </tr>
                {rows}
            </table>
        </body>
        </html>
        """
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r["success"])
        failed = total - passed
        success_rate = passed / total if total > 0 else 0
        
        rows = ""
        for result in self.results:
            status = "✅ 通过" if result["success"] else "❌ 失败"
            status_class = "success" if result["success"] else "failed"
            error = result["error"] or "-"
            duration = f"{result['duration']:.2f}s" if result["duration"] else "-"
            
            rows += f"""
            <tr>
                <td>{result['file']}</td>
                <td class="{status_class}">{status}</td>
                <td>{duration}</td>
                <td>{error}</td>
            </tr>
            """
        
        html_content = html_template.format(
            total=total,
            passed=passed,
            failed=failed,
            success_rate=success_rate,
            rows=rows
        )
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"HTML报告已生成: {output_file}")

# 使用示例
if __name__ == "__main__":
    generator = DSLReportGenerator()
    generator.run_test_suite([
        "hello.dsl",
        "api_basic.dsl",
        "auth_test.dsl"
    ])
    generator.generate_html_report()
```

## Allure 报告

### 安装和配置

安装 Allure 相关包：

```bash
pip install allure-pytest
```

### 基本集成

```python
# test_allure_integration.py
import allure
from pytest_dsl import run_dsl_file

@allure.feature("API测试")
@allure.story("用户管理")
@allure.severity(allure.severity_level.CRITICAL)
def test_user_api():
    """用户API测试"""
    with allure.step("执行用户查询"):
        result = run_dsl_file("get_user.dsl")
        assert result.success
    
    with allure.step("验证响应数据"):
        # 可以添加额外的验证步骤
        pass

@allure.feature("认证测试")
@allure.story("登录功能")
def test_auth_login():
    """登录认证测试"""
    with allure.step("执行登录测试"):
        result = run_dsl_file("auth_test.dsl")
        assert result.success
```

### 添加测试数据和附件

```python
import allure
from pytest_dsl import run_dsl_file

def test_with_attachments():
    """带附件的测试"""
    # 添加测试数据
    allure.attach("用户ID: 123", name="测试数据", attachment_type=allure.attachment_type.TEXT)
    
    result = run_dsl_file("detailed_test.dsl")
    
    # 添加执行结果作为附件
    allure.attach(
        f"执行时间: {result.duration}s\n错误信息: {result.error_message}",
        name="执行结果",
        attachment_type=allure.attachment_type.TEXT
    )
    
    assert result.success
```

### 生成 Allure 报告

```bash
# 运行测试并生成数据
pytest --alluredir=allure-results

# 启动 Allure 服务查看报告
allure serve allure-results

# 生成静态报告
allure generate allure-results -o allure-report --clean
```

## JSON 报告

### 生成 JSON 格式报告

```python
# json_report_generator.py
import json
import datetime
from pytest_dsl import run_dsl_file

class JSONReportGenerator:
    def __init__(self):
        self.report_data = {
            "timestamp": datetime.datetime.now().isoformat(),
            "summary": {},
            "tests": []
        }
    
    def run_and_report(self, dsl_files):
        """运行测试并生成JSON报告"""
        for dsl_file in dsl_files:
            result = run_dsl_file(dsl_file)
            
            test_data = {
                "name": dsl_file,
                "status": "passed" if result.success else "failed",
                "duration": result.duration,
                "error_message": result.error_message,
                "timestamp": datetime.datetime.now().isoformat()
            }
            
            self.report_data["tests"].append(test_data)
        
        # 生成摘要
        total = len(self.report_data["tests"])
        passed = sum(1 for t in self.report_data["tests"] if t["status"] == "passed")
        failed = total - passed
        
        self.report_data["summary"] = {
            "total": total,
            "passed": passed,
            "failed": failed,
            "success_rate": passed / total if total > 0 else 0
        }
    
    def save_report(self, filename="dsl_report.json"):
        """保存JSON报告"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.report_data, f, indent=2, ensure_ascii=False)
        
        print(f"JSON报告已生成: {filename}")

# 使用示例
if __name__ == "__main__":
    generator = JSONReportGenerator()
    generator.run_and_report([
        "hello.dsl",
        "api_basic.dsl",
        "auth_test.dsl"
    ])
    generator.save_report()
```

## 集成测试报告

### 多格式报告生成

```python
# comprehensive_reporter.py
from pytest_dsl import run_dsl_file
import json
import datetime
import csv

class ComprehensiveReporter:
    def __init__(self):
        self.results = []
    
    def run_test_suite(self, test_config):
        """根据配置运行测试套件"""
        for test_group in test_config["test_groups"]:
            group_name = test_group["name"]
            
            for dsl_file in test_group["files"]:
                result = run_dsl_file(dsl_file)
                
                self.results.append({
                    "group": group_name,
                    "file": dsl_file,
                    "success": result.success,
                    "duration": result.duration,
                    "error": result.error_message,
                    "timestamp": datetime.datetime.now().isoformat()
                })
    
    def generate_all_reports(self):
        """生成所有格式的报告"""
        self.generate_html_report()
        self.generate_json_report()
        self.generate_csv_report()
        self.generate_summary_report()
    
    def generate_csv_report(self):
        """生成CSV报告"""
        with open("dsl_report.csv", 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["测试组", "文件", "状态", "执行时间", "错误信息", "时间戳"])
            
            for result in self.results:
                writer.writerow([
                    result["group"],
                    result["file"],
                    "通过" if result["success"] else "失败",
                    result["duration"],
                    result["error"] or "",
                    result["timestamp"]
                ])
    
    def generate_summary_report(self):
        """生成摘要报告"""
        summary = {}
        for result in self.results:
            group = result["group"]
            if group not in summary:
                summary[group] = {"total": 0, "passed": 0, "failed": 0}
            
            summary[group]["total"] += 1
            if result["success"]:
                summary[group]["passed"] += 1
            else:
                summary[group]["failed"] += 1
        
        with open("summary.txt", 'w', encoding='utf-8') as f:
            f.write("DSL测试执行摘要\n")
            f.write("=" * 50 + "\n\n")
            
            overall_total = sum(g["total"] for g in summary.values())
            overall_passed = sum(g["passed"] for g in summary.values())
            overall_failed = sum(g["failed"] for g in summary.values())
            
            f.write(f"总体统计:\n")
            f.write(f"  总测试数: {overall_total}\n")
            f.write(f"  通过: {overall_passed}\n")
            f.write(f"  失败: {overall_failed}\n")
            f.write(f"  成功率: {overall_passed/overall_total:.1%}\n\n")
            
            f.write("分组统计:\n")
            for group, stats in summary.items():
                success_rate = stats["passed"] / stats["total"] if stats["total"] > 0 else 0
                f.write(f"  {group}:\n")
                f.write(f"    总数: {stats['total']}, 通过: {stats['passed']}, 失败: {stats['failed']}, 成功率: {success_rate:.1%}\n")

# 测试配置示例
test_config = {
    "test_groups": [
        {
            "name": "基础功能测试",
            "files": ["hello.dsl", "basic_syntax.dsl", "builtin_keywords.dsl"]
        },
        {
            "name": "API测试",
            "files": ["api_basic.dsl", "api_params.dsl", "api_capture.dsl"]
        },
        {
            "name": "认证测试",
            "files": ["auth_test.dsl"]
        }
    ]
}

# 使用示例
if __name__ == "__main__":
    reporter = ComprehensiveReporter()
    reporter.run_test_suite(test_config)
    reporter.generate_all_reports()
    print("所有格式的报告已生成完成！")
```

## 性能报告

### 执行时间分析

```python
# performance_reporter.py
import time
import statistics
from pytest_dsl import run_dsl_file

class PerformanceReporter:
    def __init__(self):
        self.performance_data = []
    
    def benchmark_test(self, dsl_file, iterations=5):
        """性能基准测试"""
        execution_times = []
        
        for i in range(iterations):
            start_time = time.time()
            result = run_dsl_file(dsl_file)
            end_time = time.time()
            
            execution_time = end_time - start_time
            execution_times.append(execution_time)
            
            print(f"第{i+1}次执行: {execution_time:.3f}s, 状态: {'成功' if result.success else '失败'}")
        
        # 统计分析
        avg_time = statistics.mean(execution_times)
        min_time = min(execution_times)
        max_time = max(execution_times)
        std_dev = statistics.stdev(execution_times) if len(execution_times) > 1 else 0
        
        performance_info = {
            "file": dsl_file,
            "iterations": iterations,
            "avg_time": avg_time,
            "min_time": min_time,
            "max_time": max_time,
            "std_dev": std_dev,
            "execution_times": execution_times
        }
        
        self.performance_data.append(performance_info)
        return performance_info
    
    def generate_performance_report(self):
        """生成性能报告"""
        with open("performance_report.txt", 'w', encoding='utf-8') as f:
            f.write("DSL性能测试报告\n")
            f.write("=" * 50 + "\n\n")
            
            for data in self.performance_data:
                f.write(f"文件: {data['file']}\n")
                f.write(f"执行次数: {data['iterations']}\n")
                f.write(f"平均时间: {data['avg_time']:.3f}s\n")
                f.write(f"最短时间: {data['min_time']:.3f}s\n")
                f.write(f"最长时间: {data['max_time']:.3f}s\n")
                f.write(f"标准差: {data['std_dev']:.3f}s\n")
                f.write("-" * 30 + "\n")

# 使用示例
if __name__ == "__main__":
    reporter = PerformanceReporter()
    
    # 对不同测试文件进行性能测试
    reporter.benchmark_test("hello.dsl", 10)
    reporter.benchmark_test("api_basic.dsl", 5)
    
    reporter.generate_performance_report()
```

## 最佳实践

### 1. 报告策略

- **开发阶段**: 使用详细的控制台输出和 HTML 报告
- **CI/CD**: 使用 JSON 报告便于自动化处理
- **发布前**: 使用 Allure 生成专业报告

### 2. 报告存储

```bash
# 创建报告目录结构
reports/
├── html/
├── json/
├── allure-results/
├── allure-report/
└── archives/
    ├── 2024-01-01/
    └── 2024-01-02/
```

### 3. 自动化报告

在 CI/CD 中集成自动报告生成：

```yaml
# .github/workflows/test-with-reports.yml
- name: Run tests and generate reports
  run: |
    pytest --alluredir=allure-results --html=report.html
    
- name: Generate Allure report
  run: |
    allure generate allure-results -o allure-report
    
- name: Archive reports
  uses: actions/upload-artifact@v2
  with:
    name: test-reports
    path: |
      report.html
      allure-report/
```

通过这些报告功能，您可以全面了解测试执行情况，快速定位问题，并生成专业的测试文档。选择合适的报告格式和工具，可以大大提高测试管理的效率。 