import sys
from PyQt5.QtWidgets import QApplication, QMessageBox
from ui.main_window import MainWindow
from utils.logger import logger

def exception_hook(exctype, value, traceback):
    """
    全局异常处理钩子
    
    捕获所有未处理的异常，记录日志并显示错误对话框
    """
    # 记录异常信息到日志
    logger.error("未捕获的异常", exc_info=(exctype, value, traceback))
    
    # 确保在Qt事件循环中显示错误对话框
    def show_error_dialog():
        error_box = QMessageBox()
        error_box.setIcon(QMessageBox.Critical)
        error_box.setWindowTitle("错误")
        error_box.setText("程序发生未知错误")
        error_box.setInformativeText(str(value))
        error_box.setDetailedText("详细错误信息已记录到日志文件中。")
        error_box.exec_()
    
    # 如果在主线程中，直接显示对话框
    if QApplication.instance() is not None:
        show_error_dialog()
    else:
        # 如果在其他线程中，将对话框显示推迟到主线程
        QApplication.instance().processEvents()

def main():
    """
    应用程序入口函数
    
    初始化Qt应用程序，创建并显示主窗口
    """
    # 创建Qt应用程序实例
    app = QApplication(sys.argv)
    
    # 设置全局异常处理钩子
    sys.excepthook = exception_hook
    
    try:
        # 创建并显示主窗口
        window = MainWindow()
        window.show()
        
        # 启动应用程序事件循环
        sys.exit(app.exec_())
        
    except Exception as e:
        logger.error(f"应用程序启动失败: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()