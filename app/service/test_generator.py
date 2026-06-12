"""
测试文件生成器 —— 将数据库中的用例渲染为可执行的 pytest 文件
"""
import os
import tempfile
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

TEMPLATE_DIR = Path(__file__).parent.parent / "templates"


class TestFileGenerator:
    """将测试用例数据渲染为pytest测试文件"""

    def __init__(self):
        self.env = Environment(
            loader=FileSystemLoader(str(TEMPLATE_DIR)),
            autoescape=select_autoescape([]),   # .py 文件不需要 HTML 转义
            trim_blocks=True,   # 去除 block 后的第一个换行
            lstrip_blocks=True, # 去除 block 前的空白
        )
        self.template = self.env.get_template("test_template.py.j2")

    def generate(
            self,
            cases: list[dict],
            base_url: str,
            project_name: str = "HappyTest",
    ) -> str:
        """
        生成测试文件并写入临时目录。
        :param cases: 测试用例列表（从数据库查询得到）
        :param base_url: 被测API的基础URL
        :param project_name: 项目名称
        :return: 生成的测试文件路径
        """
        # 渲染模板
        content = self.template.render(
            cases=cases,
            base_url=base_url,
            project_name=project_name,
            generate_at=datetime.now().isoformat(),
        )

        #写入临时文件
        test_dir = Path(tempfile.gettempdir()) / "happytest_runs"
        test_dir.mkdir(exist_ok=True)

        # 文件名包含时间戳，避免冲突
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        test_file = test_dir / f"test_generated_{timestamp}.py"

        test_file.write_text(content, encoding="utf-8")

        return str(test_file)

    def cleanup(self, file_path: str) -> None:
        """清理生成的临时测试文件"""
        try:
            os.unlink(file_path)
        except OSError:
            pass