# 这是一个适配原有main.py的文件，重定向到新的CLI入口
# 保留此文件是为了向后兼容

from pytest_dsl.cli import *

if __name__ == '__main__':
    main()
