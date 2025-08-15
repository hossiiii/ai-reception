"""Response templates for AI reception system to reduce API calls"""

from typing import Any


class ResponseTemplates:
    """Template-based responses for common reception scenarios"""

    # 初回挨拶
    GREETING = """いらっしゃいませ。音声受付システムです。
会社名、お名前、ご用件をお聞かせください。"""

    # 情報確認
    CONFIRMATION = """以下の情報で間違いございませんでしょうか？
・会社名：{company}
・お名前：{name}
・訪問目的：{purpose}

情報が正しい場合は「はい」、修正が必要な場合は「いいえ」とお答えください。"""

    # 情報修正後の再確認
    RECONFIRMATION = """修正いたしました。以下の情報で間違いございませんでしょうか？
・会社名：{company}
・お名前：{name}
・訪問目的：{purpose}

情報が正しい場合は「はい」、さらに修正が必要な場合は修正内容をお教えください。"""

    # 情報不足時の追加質問
    MISSING_INFO_SINGLE = """申し訳ございません。{missing_field}を教えていただけますでしょうか？"""

    MISSING_INFO_MULTIPLE = """申し訳ございません。以下の情報が不足しています：
{missing_fields}

例: 株式会社テストの山田太郎です。本日10時から貴社の田中様とお約束をいただいております。"""

    # 訪問目的の確認
    ASK_PURPOSE = """ありがとうございます、{company}の{name}様。
本日はどのようなご用件でお越しでしょうか？"""

    # 情報確認完了
    INFO_CONFIRMED = """ありがとうございます。確認いたしました。処理を進めさせていただきます。"""

    INFO_CONFIRMED_WITH_PURPOSE = """ありがとうございます。確認いたしました。
{purpose}の件で承りました。処理を進めさせていただきます。"""

    # 配達業者向け
    DELIVERY_GUIDANCE = """{company}様、お疲れ様です。
配達の件でお越しいただき、ありがとうございます。

・置き配の場合: 玄関前にお荷物をお置きください
・サインが必要な場合: 奥の呼び鈴を押してお待ちください

配達完了後は、そのままお帰りいただけます。
ありがとうございました。"""

    # 営業訪問者向け
    SALES_GUIDANCE = """{name}様、お疲れ様です。

申し訳ございませんが、弊社では新規のお取引については
現在お断りさせていただいております。

もしお名刺や資料をお預けいただける場合は、
こちらにお預けください。
必要に応じて後日、担当者よりご連絡差し上げます。"""

    # 予約確認済み
    APPOINTMENT_FOUND = """承知いたしました。
{visitor_name}様の{time}のご予約を確認いたしました。

{company}の{name}様、本日はお忙しい中お越しいただき、
ありがとうございます。

会議室は{room_name}になります。
どうぞよろしくお願いいたします。"""

    # 予約なし
    APPOINTMENT_NOT_FOUND = """{company}の{name}様、お疲れ様です。

申し訳ございませんが、本日の予約を確認できませんでした。

恐れ入りますが、事前予約制となっております。
お手数ですが、担当者にご連絡の上、
改めて予約をお取りください。"""

    # エラー・不明瞭な回答
    UNCLEAR_CONFIRMATION = """申し訳ございません。「はい」または「いいえ」でお答えください。

情報が正しい場合は「はい」
修正が必要な場合は「いいえ」または修正内容を直接お教えください。"""

    # 情報修正の案内
    CORRECTION_REQUEST = """承知いたしました。お手数ですが、会社名・お名前・訪問目的を再度教えてください。

例: 株式会社テストの山田太郎です。本日10時から貴社の田中様とお約束をいただいております。"""

    # システムエラー
    SYSTEM_ERROR = """申し訳ございません。システムの不具合が発生しました。
スタッフをお呼びいたします。少々お待ちください。"""

    @classmethod
    def format_template(cls, template: str, **kwargs: Any) -> str:
        """Format template with provided parameters"""
        try:
            return template.format(**kwargs)
        except KeyError as e:
            print(f"Template formatting error: Missing key {e}")
            return template

    @classmethod
    def get_missing_info_message(cls, missing_fields: list[str]) -> str:
        """Generate message for missing information"""
        if len(missing_fields) == 1:
            field_name_map = {
                "company": "会社名",
                "name": "お名前",
                "purpose": "訪問目的"
            }
            field_name = field_name_map.get(missing_fields[0], missing_fields[0])
            return cls.format_template(cls.MISSING_INFO_SINGLE, missing_field=field_name)
        else:
            field_names = []
            for field in missing_fields:
                if field == "company":
                    field_names.append("会社名")
                elif field == "name":
                    field_names.append("お名前")
                elif field == "purpose":
                    field_names.append("訪問目的")

            return cls.format_template(
                cls.MISSING_INFO_MULTIPLE,
                missing_fields="・" + "\n・".join(field_names)
            )

    @classmethod
    def get_confirmation_message(cls, visitor_info: dict[str, Any], is_reconfirmation: bool = False) -> str:
        """Get confirmation message based on visitor information"""
        template = cls.RECONFIRMATION if is_reconfirmation else cls.CONFIRMATION

        return cls.format_template(
            template,
            company=visitor_info.get('company', '不明'),
            name=visitor_info.get('name', '不明'),
            purpose=visitor_info.get('purpose', '不明')
        )

    @classmethod
    def get_guidance_message(cls, visitor_type: str, visitor_info: dict[str, Any],
                            calendar_result: dict[str, Any] = None) -> str:
        """Get guidance message based on visitor type and context"""

        if visitor_type == "delivery":
            return cls.format_template(
                cls.DELIVERY_GUIDANCE,
                company=visitor_info.get('company', '配送業者')
            )

        elif visitor_type == "sales":
            return cls.format_template(
                cls.SALES_GUIDANCE,
                name=visitor_info.get('name', '営業担当')
            )

        elif visitor_type == "appointment":
            if calendar_result and calendar_result.get("found"):
                # Extract time from calendar result if available
                time = ""
                if calendar_result.get("events"):
                    # Assuming first event has the time
                    time = "本日"  # Can be enhanced to extract actual time

                room_name = calendar_result.get("roomName", "会議室")

                return cls.format_template(
                    cls.APPOINTMENT_FOUND,
                    visitor_name=visitor_info.get('name', ''),
                    company=visitor_info.get('company', ''),
                    name=visitor_info.get('name', ''),
                    time=time,
                    room_name=room_name
                )
            else:
                return cls.format_template(
                    cls.APPOINTMENT_NOT_FOUND,
                    company=visitor_info.get('company', ''),
                    name=visitor_info.get('name', '')
                )

        # Default fallback
        return cls.SYSTEM_ERROR
