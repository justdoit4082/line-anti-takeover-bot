def is_user_group_admin(user_id: str, group_admins: list) -> bool:
    """
    檢查某個 user_id 是否在群組管理員名單中
    :param user_id: 使用者 LINE ID
    :param group_admins: 管理員 user_id 清單
    :return: 是或否
    """
    return user_id in group_admins
