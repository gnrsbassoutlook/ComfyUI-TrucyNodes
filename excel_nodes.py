import os
import csv
import re
import openpyxl


# ========================================================
# Excel / CSV 公共读取工具
# ========================================================
class _TrucyExcelBase:
    VALID_EXTENSIONS = (".xlsx", ".csv")

    @staticmethod
    def clean_path(excel_path):
        return str(excel_path).strip().replace('"', "")

    @classmethod
    def resolve_file(cls, excel_path):
        """
        如果输入文件夹，则自动选择按文件名排序后的第一个
        .xlsx 或 .csv 文件。
        """
        clean_path = cls.clean_path(excel_path)

        if os.path.isdir(clean_path):
            files = [
                file_name
                for file_name in os.listdir(clean_path)
                if file_name.lower().endswith(cls.VALID_EXTENSIONS)
            ]

            files.sort(key=str.lower)

            if not files:
                return None, (
                    "Error: No .xlsx or .csv files found in directory"
                )

            target_file = os.path.join(clean_path, files[0])

            print(
                "[TrucyNodes] Excel directory mode. "
                f"Auto-selected file: {target_file}"
            )

            return target_file, None

        if not os.path.isfile(clean_path):
            return None, f"Error: File not found at {clean_path}"

        return clean_path, None

    @staticmethod
    def convert_value(cell_value):
        """
        将一个单元格同时转换为：
        STRING、INT、FLOAT
        """
        if cell_value is None or str(cell_value).strip() == "":
            return "N/A", 0, 0.0

        full_string = str(cell_value)

        # 从复杂文本中提取第一个整数或小数
        number_match = re.search(
            r"[-+]?(?:\d+\.\d+|\d+|\.\d+)",
            full_string,
        )

        result_int = 0
        result_float = 0.0

        if number_match:
            number_string = number_match.group()

            try:
                result_float = float(number_string)
                result_int = int(result_float)
            except (ValueError, TypeError, OverflowError):
                result_int = 0
                result_float = 0.0

        return full_string, result_int, result_float

    @classmethod
    def get_change_token(cls, excel_path):
        """
        文件发生修改时，让 ComfyUI 重新读取。
        """
        target_file, error = cls.resolve_file(excel_path)

        if error or target_file is None:
            return float("NaN")

        try:
            return os.path.getmtime(target_file)
        except OSError:
            return float("NaN")

    @classmethod
    def read_multiple_cells(
        cls,
        excel_path,
        sheet_name,
        positions,
    ):
        """
        一次读取多个单元格。

        positions 格式：
        [
            (row_1, column_1),
            (row_2, column_2),
            ...
        ]
        """
        target_file, error = cls.resolve_file(excel_path)

        if error:
            results = []

            for _ in positions:
                results.extend((error, 0, 0.0))

            return tuple(results)

        extension = os.path.splitext(target_file)[1].lower()

        try:
            # =================================================
            # CSV 读取
            # CSV 不使用 sheet_name
            # =================================================
            if extension == ".csv":
                with open(
                    target_file,
                    "r",
                    encoding="utf-8-sig",
                    errors="replace",
                    newline="",
                ) as csv_file:
                    csv_data = list(csv.reader(csv_file))

                results = []

                for row, column in positions:
                    if not (1 <= row <= len(csv_data)):
                        results.extend(
                            (
                                f"Error: Row {row} out of range in CSV",
                                0,
                                0.0,
                            )
                        )
                        continue

                    current_row = csv_data[row - 1]

                    if not (1 <= column <= len(current_row)):
                        results.extend(
                            (
                                (
                                    f"Error: Column {column} out of "
                                    f"range in CSV row {row}"
                                ),
                                0,
                                0.0,
                            )
                        )
                        continue

                    cell_value = current_row[column - 1]
                    results.extend(cls.convert_value(cell_value))

                return tuple(results)

            # =================================================
            # XLSX 读取
            # 多个单元格只打开一次工作簿，提高效率
            # =================================================
            if extension == ".xlsx":
                workbook = openpyxl.load_workbook(
                    target_file,
                    data_only=True,
                    read_only=True,
                )

                try:
                    if sheet_name not in workbook.sheetnames:
                        error_message = (
                            f"Error: Sheet '{sheet_name}' not found"
                        )

                        results = []

                        for _ in positions:
                            results.extend(
                                (error_message, 0, 0.0)
                            )

                        return tuple(results)

                    sheet = workbook[sheet_name]
                    results = []

                    for row, column in positions:
                        cell_value = sheet.cell(
                            row=row,
                            column=column,
                        ).value

                        results.extend(
                            cls.convert_value(cell_value)
                        )

                    return tuple(results)

                finally:
                    workbook.close()

            if extension == ".xls":
                error_message = (
                    "Error: Legacy .xls format is unsupported. "
                    "Please save it as .xlsx or .csv"
                )
            else:
                error_message = (
                    f"Error: Unsupported file format: {extension}"
                )

            results = []

            for _ in positions:
                results.extend((error_message, 0, 0.0))

            return tuple(results)

        except Exception as error:
            error_message = f"Error: {error}"
            results = []

            for _ in positions:
                results.extend((error_message, 0, 0.0))

            return tuple(results)


# ========================================================
# 原来的单路版本
# 保留这个类，避免旧工作流丢失节点
# ========================================================
class TrucyExcelReader(_TrucyExcelBase):
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "excel_path": (
                    "STRING",
                    {
                        "default": "C:\\example.xlsx",
                    },
                ),
                "sheet_name": (
                    "STRING",
                    {
                        "default": "Sheet1",
                    },
                ),
                "row": (
                    "INT",
                    {
                        "default": 1,
                        "min": 1,
                        "max": 999999,
                    },
                ),
                "column": (
                    "INT",
                    {
                        "default": 1,
                        "min": 1,
                        "max": 999,
                    },
                ),
            }
        }

    RETURN_TYPES = (
        "STRING",
        "INT",
        "FLOAT",
    )

    RETURN_NAMES = (
        "string",
        "int",
        "float",
    )

    FUNCTION = "read_cell"
    CATEGORY = "TrucyNodes/Excel"

    @classmethod
    def IS_CHANGED(
        cls,
        excel_path,
        sheet_name,
        row,
        column,
    ):
        return cls.get_change_token(excel_path)

    def read_cell(
        self,
        excel_path,
        sheet_name,
        row,
        column,
    ):
        return self.read_multiple_cells(
            excel_path=excel_path,
            sheet_name=sheet_name,
            positions=[
                (row, column),
            ],
        )


# ========================================================
# 多路 Excel Reader 基类
# ========================================================
class _TrucyExcelMultiReader(_TrucyExcelBase):
    CHANNELS = 5

    FUNCTION = "read_cells"
    CATEGORY = "TrucyNodes/Excel"

    @classmethod
    def INPUT_TYPES(cls):
        required = {
            "excel_path": (
                "STRING",
                {
                    "default": "C:\\example.xlsx",
                },
            ),
            "sheet_name": (
                "STRING",
                {
                    "default": "Sheet1",
                },
            ),
        }

        for index in range(1, cls.CHANNELS + 1):
            required[f"row_{index}"] = (
                "INT",
                {
                    "default": index,
                    "min": 1,
                    "max": 999999,
                },
            )

            required[f"column_{index}"] = (
                "INT",
                {
                    "default": 1,
                    "min": 1,
                    "max": 999,
                },
            )

        return {
            "required": required,
        }

    @classmethod
    def IS_CHANGED(
        cls,
        excel_path,
        sheet_name,
        **kwargs,
    ):
        return cls.get_change_token(excel_path)

    def read_cells(
        self,
        excel_path,
        sheet_name,
        **kwargs,
    ):
        positions = []

        for index in range(1, self.CHANNELS + 1):
            row = kwargs.get(f"row_{index}", index)
            column = kwargs.get(f"column_{index}", 1)

            positions.append((row, column))

        return self.read_multiple_cells(
            excel_path=excel_path,
            sheet_name=sheet_name,
            positions=positions,
        )


# ========================================================
# 5 路版本
# 每一路输出 STRING、INT、FLOAT
# 合计 15 个输出接口
# ========================================================
class TrucyExcelReader5(_TrucyExcelMultiReader):
    CHANNELS = 5

    RETURN_TYPES = (
        "STRING", "INT", "FLOAT",
        "STRING", "INT", "FLOAT",
        "STRING", "INT", "FLOAT",
        "STRING", "INT", "FLOAT",
        "STRING", "INT", "FLOAT",
    )

    RETURN_NAMES = (
        "string_1", "int_1", "float_1",
        "string_2", "int_2", "float_2",
        "string_3", "int_3", "float_3",
        "string_4", "int_4", "float_4",
        "string_5", "int_5", "float_5",
    )


# ========================================================
# 10 路版本
# 每一路输出 STRING、INT、FLOAT
# 合计 30 个输出接口
# ========================================================
class TrucyExcelReader10(_TrucyExcelMultiReader):
    CHANNELS = 10

    RETURN_TYPES = (
        "STRING", "INT", "FLOAT",
        "STRING", "INT", "FLOAT",
        "STRING", "INT", "FLOAT",
        "STRING", "INT", "FLOAT",
        "STRING", "INT", "FLOAT",
        "STRING", "INT", "FLOAT",
        "STRING", "INT", "FLOAT",
        "STRING", "INT", "FLOAT",
        "STRING", "INT", "FLOAT",
        "STRING", "INT", "FLOAT",
    )

    RETURN_NAMES = (
        "string_1", "int_1", "float_1",
        "string_2", "int_2", "float_2",
        "string_3", "int_3", "float_3",
        "string_4", "int_4", "float_4",
        "string_5", "int_5", "float_5",
        "string_6", "int_6", "float_6",
        "string_7", "int_7", "float_7",
        "string_8", "int_8", "float_8",
        "string_9", "int_9", "float_9",
        "string_10", "int_10", "float_10",
    )


# ========================================================
# 独立注册映射
# ========================================================
NODE_CLASS_MAPPINGS = {
    "TrucyExcelReader": TrucyExcelReader,
    "TrucyExcelReader5": TrucyExcelReader5,
    "TrucyExcelReader10": TrucyExcelReader10,
}


NODE_DISPLAY_NAME_MAPPINGS = {
    "TrucyExcelReader": "Excel-Reader-Trucy",
    "TrucyExcelReader5": "Excel-Reader-5-Trucy",
    "TrucyExcelReader10": "Excel-Reader-10-Trucy",
}