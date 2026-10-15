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
        if cell_value is None or str(cell_value).strip() == "":
            return "N/A", 0, 0.0

        full_string = str(cell_value)

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
        target_file, error = cls.resolve_file(excel_path)

        if error:
            results = []
            for _ in positions:
                results.extend((error, 0, 0.0))
            return tuple(results)

        extension = os.path.splitext(target_file)[1].lower()

        try:
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
# 单路版本
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
    CHANNELS = 6

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

        # 读取交错结果: (Text_1, Int_1, Float_1, Text_2, Int_2, Float_2, ...)
        raw_results = self.read_multiple_cells(
            excel_path=excel_path,
            sheet_name=sheet_name,
            positions=positions,
        )

        # 按照类型分类聚合: 先全部 Text，再全部 Int，最后全部 Float
        texts = raw_results[0::3]
        ints = raw_results[1::3]
        floats = raw_results[2::3]

        return tuple(texts + ints + floats)


# ========================================================
# 6 路版本 (TrucyExcelReader6)
# ========================================================
class TrucyExcelReader6(_TrucyExcelMultiReader):
    CHANNELS = 6

    # 先 6 个 STRING，再 6 个 INT，最后 6 个 FLOAT
    RETURN_TYPES = (
        "STRING", "STRING", "STRING", "STRING", "STRING", "STRING",
        "INT", "INT", "INT", "INT", "INT", "INT",
        "FLOAT", "FLOAT", "FLOAT", "FLOAT", "FLOAT", "FLOAT",
    )

    RETURN_NAMES = (
        "Text_1", "Text_2", "Text_3", "Text_4", "Text_5", "Text_6",
        "Int_1", "Int_2", "Int_3", "Int_4", "Int_5", "Int_6",
        "Float_1", "Float_2", "Float_3", "Float_4", "Float_5", "Float_6",
    )


# ========================================================
# 10 路版本 (TrucyExcelReader10)
# ========================================================
class TrucyExcelReader10(_TrucyExcelMultiReader):
    CHANNELS = 10

    # 先 10 个 STRING，再 10 个 INT，最后 10 个 FLOAT
    RETURN_TYPES = (
        "STRING", "STRING", "STRING", "STRING", "STRING",
        "STRING", "STRING", "STRING", "STRING", "STRING",
        "INT", "INT", "INT", "INT", "INT",
        "INT", "INT", "INT", "INT", "INT",
        "FLOAT", "FLOAT", "FLOAT", "FLOAT", "FLOAT",
        "FLOAT", "FLOAT", "FLOAT", "FLOAT", "FLOAT",
    )

    RETURN_NAMES = (
        "Text_1", "Text_2", "Text_3", "Text_4", "Text_5",
        "Text_6", "Text_7", "Text_8", "Text_9", "Text_10",
        "Int_1", "Int_2", "Int_3", "Int_4", "Int_5",
        "Int_6", "Int_7", "Int_8", "Int_9", "Int_10",
        "Float_1", "Float_2", "Float_3", "Float_4", "Float_5",
        "Float_6", "Float_7", "Float_8", "Float_9", "Float_10",
    )


NODE_CLASS_MAPPINGS = {
    "TrucyExcelReader": TrucyExcelReader,
    "TrucyExcelReader6": TrucyExcelReader6,
    "TrucyExcelReader10": TrucyExcelReader10,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "TrucyExcelReader": "Excel-Reader-Trucy",
    "TrucyExcelReader6": "Excel-Reader-6-Trucy",
    "TrucyExcelReader10": "Excel-Reader-10-Trucy",
}