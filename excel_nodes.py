import os
import openpyxl
import torch
import re  # 导入正则表达式库用于提取数字

class TrucyExcelReader:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "excel_path": ("STRING", {"default": "C:\\example.xlsx"}),
                "sheet_name": ("STRING", {"default": "Sheet1"}),
                "row": ("INT", {"default": 1, "min": 1, "max": 999999}),
                "column": ("INT", {"default": 1, "min": 1, "max": 999}),
            }
        }

    RETURN_TYPES = ("STRING", "INT", "FLOAT")
    RETURN_NAMES = ("string", "int", "float")
    FUNCTION = "read_cell"
    CATEGORY = "TrucyNodes/Excel"

    @classmethod
    def IS_CHANGED(cls, excel_path, sheet_name, row, column):
        # 保持缓存刷新逻辑
        return f"{excel_path}_{sheet_name}_{row}_{column}"

    def read_cell(self, excel_path, sheet_name, row, column):
        # 1. 路径清洗
        clean_path = excel_path.strip().replace('"', '')
        
        if not os.path.exists(clean_path):
            return (f"Error: File not found at {clean_path}", 0, 0.0)

        try:
            # 2. 读取 Excel
            workbook = openpyxl.load_workbook(clean_path, data_only=True, read_only=True)
            if sheet_name not in workbook.sheetnames:
                return (f"Error: Sheet '{sheet_name}' not found", 0, 0.0)
            
            sheet = workbook[sheet_name]
            cell_value = sheet.cell(row=row, column=column).value
            workbook.close()

            if cell_value is None:
                return ("N/A", 0, 0.0)

            # 3. 原始字符串处理
            full_str = str(cell_value)

            # --- 4. 智能数字提取逻辑 ---
            # 正则表达式解释：
            # [-+]?          : 可能有正负号
            # \d*\.\d+       : 匹配小数（如 01.25, .25）
            # |              : 或者
            # \d+            : 匹配整数
            # re.search 会只找第一个匹配项
            number_match = re.search(r"[-+]?\d*\.\d+|[-+]?\d+", full_str)

            res_float = 0.0
            res_int = 0

            if number_match:
                num_str = number_match.group() # 提取到的第一个数字字符串
                try:
                    res_float = float(num_str)
                    res_int = int(res_float) # 向下取整转为整数
                except:
                    pass

            # 5. 返回结果
            # string: 返回原始完整文本
            # int: 返回提取到的第一个数字的整数部分
            # float: 返回提取到的第一个数字的小数
            return (full_str, res_int, res_float)

        except Exception as e:
            return (f"Error: {str(e)}", 0, 0.0)

NODE_CLASS_MAPPINGS = {
    "TrucyExcelReader": TrucyExcelReader
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "TrucyExcelReader": "Excel Cell Reader (Trucy)"
}