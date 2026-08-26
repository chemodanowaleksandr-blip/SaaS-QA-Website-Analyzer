import streamlit as st
from database import register_user, verify_user

def render_auth_section():
    """Отрисовывает блок авторизации/регистрации в боковой панели.
    
    Возвращает словарь с данными пользователя, если он вошел, или None.
    """
    # Инициализируем переменные сессии для хранения статуса входа
    if "auth_user" not in st.session_state:
        st.session_state["auth_user"] = None

    # Если пользователь уже успешно авторизован
    if st.session_state["auth_user"]:
        user_data = st.session_state["auth_user"]
        st.sidebar.success(f"👤 Вошел как: **{user_data['username']}**")
        
        # Кнопка выхода из аккаунта
        if st.sidebar.button("Выйти из системы", type="secondary"):
            st.session_state["auth_user"] = None
            st.rerun()
            
        return st.session_state["auth_user"]

    # Если пользователь еще не вошел — показываем переключатель режимов
    st.sidebar.subheader("🔐 Авторизация системы")
    auth_mode = st.sidebar.radio("Выберите действие:", ["Вход", "Регистрация"])

    # Форма для ввода учетных данных
    with st.sidebar.form(key="user_auth_form"):
        username_input = st.text_input("Логин (email или имя):").strip()
        password_input = st.text_input("Пароль:", type="password")
        submit_auth = st.form_submit_button("Подтвердить", type="primary")

    if submit_auth:
        if not username_input or not password_input:
            st.sidebar.error("Заполните все поля формы!")
            return None

        if auth_mode == "Вход":
            success, user_data = verify_user(username_input, password_input)
            if success:
                st.session_state["auth_user"] = user_data
                st.sidebar.success("Успешный вход в систему!")
                st.rerun()
            else:
                st.sidebar.error("Неверный логин или пароль!")
                
        elif auth_mode == "Регистрация":
            success, message = register_user(username_input, password_input)
            if success:
                st.sidebar.success(message)
                st.sidebar.info("Теперь переключитесь на вкладку 'Вход'.")
            else:
                st.sidebar.error(message)

    return None
