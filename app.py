import streamlit as st
from database import engine, SessionLocal, Base
import models
import pandas as pd
from sqlalchemy import func
from views.edital import show_edital_view
from views.dashboard import show_dashboard_view
from views.flashcards import show_flashcards_view


st.set_page_config(page_title="Hunter-Posse: Gestor de Concursos", layout="wide")

# Cria o banco de dados (tables) caso não existam
Base.metadata.create_all(bind=engine)


def get_session():
    return SessionLocal()


menu = st.sidebar.selectbox("Navegação", ["Dashboard", "Edital Verticalizado", "Exportar Flashcards"])


if menu == "Dashboard":
    show_dashboard_view()


elif menu == "Edital Verticalizado":
    show_edital_view()


elif menu == "Exportar Flashcards":
    show_flashcards_view()
