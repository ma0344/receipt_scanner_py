# -*- coding: utf-8 -*-
from datetime import datetime
from typing import List
from util import get_exif
from Receipt import Receipt
from japanera import EraDate
# ACDataクラスのPython版


class ACData:
    """
    仕訳データを表すクラスです。
    各仕訳項目の属性を保持します。
    """

    def __init__(self):
        """
        仕訳データの初期化を行います。
        """
        self.account_no = 0
        self.row_no = 0
        self.ac_date = ""
        self.left_code = 0
        self.left_title = ""
        self.left_amount = 0
        self.right_code = 0
        self.right_title = ""
        self.right_sub_code = 0
        self.right_sub_title = ""
        self.right_amount = 0
        self.desc = ""
        self.sub_desc = ""


title_dic = {
    611: "給食用材料費",
    612: "その他の材料費",
    750: "車両燃料費",
    102: "小口  現金",
    666: "仕訳保留"
}

title_to_desc_dic = {
    "給食用材料費": "食材料費",
    "その他の材料費": "日用品費",
    "車両燃料費": "ガソリン代",
    "小口  現金": "小口現金",
    "仕訳保留": "勘定不明"

}


# 説明からタイトルコードへの辞書
desc_to_title_code_dic = {
    "ここっち 食材料費": 611,
    "食材料費": 611,
    "ここっち 日用品費": 612,
    "日用品費": 612,
    "ここっち ガソリン代": 750,
    "ガソリン代": 750,
    "未設定勘定": 666,
    "その他": 666,
    "": 666,
    "小口　現金": 102,
    "小口現金": 102
}


# タイトルコードから説明への辞書
title_code_to_desc_dic = {
    611: "食材料費",
    612: "日用品費",
    750: "ガソリン代",
    666: "勘定不明",
    102: "小口現金"
}

# 対応する値を文字列として取得


class AccCreator:
    """
    仕訳データを生成するクラスです。
    """

    def __init__(self, sheet_paths: list[str]):
        """
        コンストラクタです。

        Args:
            sheet_paths (List[str]): 処理するシートのファイルパスのリスト。
        """
        self.sheet_paths = sheet_paths
        self.csv_string_arr = self.set_csv_header()

    def set_csv_header(self) -> list[tuple[str], list[Receipt]]:
        """
        初期のCSV配列を準備します。
        この関数は、CSVファイルのヘッダー行を含む配列を作成します。
        """
        csv_arr = []
        csv_arr.append(self.set_header())
        return csv_arr

    def accCreate(self, sheet_paths=[]):
        """
        指定されたシートパスのリストから、各シートのレシートデータを処理し、
        仕訳データを生成してCSV形式で返します。

        Args:
            sheet_paths (List[str]): 処理するシートのファイルパスのリスト。

        Returns:
            tuple: ファイル名と仕訳データのCSV文字列を含むタプル。
        """
        # 初期のCSV配列を準備
        if sheet_paths != []:
            self.sheet_paths = sheet_paths
        sheet_collection: list[tuple[str, list[Receipt]]] = self.create_sheet_collection()
        # シートごとに仕訳を作成しaccountsに追加
        for lineIndex, sheet_data in enumerate(sheet_collection):
            sheet_date = sheet_data[0]
            receipts: list[Receipt] = sheet_data[1]
            receipts_count = len(receipts)

            # データがない場合はスキップする
            if receipts_count == 0 or (sheet_date == "" and receipts[0].date == ""):
                continue

            if sheet_date == "":
                sheet_date = receipts[0].date
            # 日付の変換とアカウント番号の設定
            data: ACData = self.create_ACData_object(lineIndex, sheet_date)
            self.csv_string_arr.extend(self.create_account_arr(receipts, data))

        # 生成されたCSV文字列を結合し、ファイル名を生成
        return_filename, return_csv = self.create_return_value(sheet_collection)
        return return_filename, return_csv

    def create_sheet_collection(self) -> list[tuple[str], list[Receipt]]:
        """
        指定されたシートパスのリストから、各シートのレシートデータを処理し、
        仕訳データを生成してCSV形式で返します。

        Args:
            sheet_paths (List[str]): 処理するシートのファイルパスのリスト。

        Returns:
            tuple: ファイル名と仕訳データのCSV文字列を含むタプル。
        """
        # 初期のCSV配列を準備
        sheet_collection: list[tuple[str, list[Receipt]]] = []
        for sheet_path in self.sheet_paths:
            # シートからEXIFデータを取得し、シートの日付とレシートリストを取得
            sheet: List[Receipt] = []
            result, sheet_date, sheet = get_exif(sheet_path)
            if not result:
                continue
            # シートの日付とレシートリストをコレクションに追加
            sheet_collection.append([sheet_date, sheet])
        return sheet_collection

    def create_ACData_object(self, lineIndex: int, sheet_date: str) -> ACData:
        date_obj = datetime.strptime(sheet_date, "%Y年%m月%d日")
        era_date = EraDate.from_date(date_obj)
        date_str = era_date.strftime("%-h.%-y/%m/%d")
        data = ACData()
        data.account_no = str(date_obj.strftime("%y%m%d")) + str(lineIndex).format(lineIndex,)
        data.ac_date = date_str
        return data

    def create_account_arr(self, receipts: list[Receipt], data: ACData) -> str:
        receipts_count = len(receipts)
        # レシートが1つの場合の処理
        if receipts_count == 1:
            return self.single_line_accounting(receipts, data)
        # レシートが複数の場合の処理
        elif receipts_count > 1:
            return self.sundries_accounting(receipts, data)

    def single_line_accounting(self, receipts: list[Receipt], data: ACData) -> list[str]:
        data.left_code = desc_to_title_code_dic.get(receipts[0].item_category)
        data.left_title = title_dic.get(data.left_code)
        if isinstance(receipts[0].amount, str):
            data.left_amount = int(receipts[0].amount) if receipts[0].amount.isnumeric() else 0
        else:
            data.left_amount = receipts[0].amount
        data.right_amount = data.left_amount
        data.desc = "ここっち " + title_code_to_desc_dic.get(data.left_code)
        data.sub_desc = receipts[0].supplyer_name
        csv_row_string = \
            [f'{data.account_no},1,"{data.ac_date}",{data.left_code},"{data.left_title}",0,"",211,"ここっち",0,0,3,0,{data.left_amount},0,'
             + f'102,"小口  現金",211,"ここっち",211,"ここっち",0,0,3,0,{data.right_amount},0,"{data.desc}","{data.sub_desc}","",0,0,0']
        return csv_row_string

    def sundries_accounting(self, receipts: list[Receipt], data: ACData):
        data.right_amount = 0
        sub_data_list: list[str] = []
        category_list: list[str] = []
        for r, receipt in enumerate(receipts, start=2):
            sub_data, csv_line_string = self.sub_line_accounting(r, receipt, data)
            data.right_amount += sub_data.left_amount
            sub_data_list.append(csv_line_string)
            category_list.append(sub_data.left_title)
            pass
        data.desc = self.get_corresponding_values_as_string(category_list)
        multi_line_arr = self.marge_sundries_accounting(data, sub_data_list)
        return multi_line_arr

    def sub_line_accounting(self, r: int, receipt: Receipt, data: ACData):
        sub_data = ACData()
        sub_data.account_no = data.account_no
        sub_data.row_no = r
        sub_data.ac_date = data.ac_date
        sub_data.left_code = desc_to_title_code_dic.get(receipt.item_category)
        sub_data.left_title = title_dic.get(sub_data.left_code)
        if isinstance(receipt.amount, str):
            sub_data.left_amount = int(receipt.amount) if receipt.amount.isnumeric() else 0
        else:
            sub_data.left_amount = receipt.amount

        sub_data.desc = "ここっち " + title_code_to_desc_dic.get(sub_data.left_code)
        sub_data.sub_desc = receipt.supplyer_name
        csv_row_string = \
            f'{sub_data.account_no},{sub_data.row_no},"{sub_data.ac_date}",{sub_data.left_code},"{sub_data.left_title}",0,"",211,"ここっち",0,0,3,0,{sub_data.left_amount},0,' + f'0,"",0,"",0,"",0,0,3,0,0,0,"{sub_data.desc}","{sub_data.sub_desc}","",0,0,0'
        return sub_data, csv_row_string

    def marge_sundries_accounting(self, data: ACData, sub_data_list):
        data.sub_desc = ""
        marged_accounting_list = [
            f'{data.account_no},1,"{data.ac_date}",0,"",0,"",0,"",0,0,3,0,0,0,'
            + f'102,"小口  現金",211,"ここっち",211,"ここっち",0,0,3,0,{data.right_amount},0,"{data.desc}","{data.sub_desc}","",0,0,0']
        marged_accounting_list.extend(sub_data_list)
        return marged_accounting_list

    def create_return_value(self, sheet_collection) -> tuple[str, str]:
        return_csv = '\n'.join(self.csv_string_arr)
        dateobj = datetime.strptime(sheet_collection[0][0], "%Y年%m月%d日")
        eradate = EraDate.from_date(dateobj)
        datestr = eradate.strftime("%-K%-y年%m月")
        time_stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return_filename = f"{datestr}_小口現金仕訳_{time_stamp}.csv"
        return return_filename, return_csv

    def set_header(self):
        """
        CSVファイルのヘッダー行を生成します。
        このヘッダー行は、仕訳データの各列の名前を定義します。

        Returns:
            str: CSVファイルのヘッダー行を含む文字列。
        """

        # dt = "2024-12-15"
        # tm = "00:00:00"
        # csv = f'//SFD FMTNAME="SIWAKE" FMTVER="3.01.00" APPNAME="会計王19 19.03.00～" APPVER="19.50.00" RTNDATE="{dt}" RTNTIME="{tm}"\r\n'
        csv = '"伝票番号","行番号","伝票日付","借方科目コード","借方科目名称","借方補助コード","借方補助科目名称","借方部門コード","借方部門名称","借方課税区分コード","借方事業分類コード","借方税処理コード","借方税率","借方金額","借方消費税","貸方科目コード","貸方科目名称","貸方補助コード","貸方補助科目名称","貸方部門コード","貸方部門名称","貸方課税区分コード","貸方事業分類コード","貸方税処理コード","貸方税率","貸方金額","貸方消費税","取引摘要","補助摘要","メモ","付箋1","付箋2","伝票種別"'

        return csv

    def get_corresponding_values_as_string(self, items):
        """
        与えられたアイテムのリストから、対応する説明を取得し、それらを結合して文字列として返します。
        説明は、タイトルコードから取得され、結合された説明は特定のバイト数制限内に収まるように切り詰められます。

        Args:
            items (list): 処理するアイテムのリスト。

        Returns:
            str: 結合された説明の文字列。
        """
        result = []
        for item in items:
            desc = title_to_desc_dic.get(item, "勘定不明")
            if desc not in result:
                result.append(desc)
        result_string = "ここっち " + " ".join(result)
        if len(result_string.encode('utf-8')) > 30:
            result_string = result_string[:15]  # 簡易的なバイト数の制限
        return result_string
