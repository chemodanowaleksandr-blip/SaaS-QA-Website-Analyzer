import streamlit as st
from database import register_user, verify_user

def render_auth_section(t):
    """Отрисовывает блок авторизации/регистрации в боковой панели.
    
    Принимает словарь локализации t для полной поддержки языков.
    """
    if "auth_user" not in st.session_state:
        st.session_state["auth_user"] = None

    if st.session_state["auth_user"]:
        user_data = st.session_state["auth_user"]
        st.sidebar.success(f"👤 {t['status_label']}: **{user_data['username']}**")
        
        if st.sidebar.button(t["logout_btn"], type="secondary"):
            st.session_state["auth_user"] = None
            st.rerun()
            
        return st.session_state["auth_user"]

    st.sidebar.subheader(t["auth_title"])
    auth_mode = st.sidebar.radio(t["auth_mode_label"], t["auth_modes"])

    with st.sidebar.form(key="user_auth_form"):
        username_input = st.text_input(t["login_user"]).strip()
        password_input = st.text_input(t["login_pass"], type="password")
        submit_auth = st.form_submit_button(t["auth_submit"], type="primary")

    if submit_auth:
        if not username_input or not password_input:
            st.sidebar.error(t["auth_empty_err"])
            return None

        # Проверяем выбранный режим (первый элемент списка — всегда вход)
        if auth_mode == t["auth_modes"][0]:
            success, user_data = verify_user(username_input, password_input)
            if success:
                st.session_state["auth_user"] = user_data
                st.sidebar.success(t["auth_login_ok"])
                st.rerun()
            else:
                st.sidebar.error(t["auth_login_fail"])
                
        # Второй элемент списка — регистрация
        elif auth_mode == t["auth_modes"][1]:
            success, message = register_user(username_input, password_input)
            if success:
                st.sidebar.success(message)
                st.sidebar.info(t["auth_reg_info"])
            else:
                st.sidebar.error(message)

    return None
