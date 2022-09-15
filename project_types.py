from typing import TypedDict

class SettingsParseBrands(TypedDict):
    setting_equal: int
    setting_greater_by: int
    setting_less_by: int
    setting_less_than: int
    setting_greater_than: int

class AuthTelegramData(TypedDict):
	id: int
	first_name: str
	last_name: str
	username: str
	photo_url: str
	auth_date:  str
	hash: str


