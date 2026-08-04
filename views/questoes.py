import streamlit as st

from database import SessionLocal
import models


@st.cache_data
def load_questoes_options():
    """Carrega editais, disciplinas e tópicos para o formulário de questões."""
    session = SessionLocal()
    try:
        editais = session.query(models.Edital).order_by(models.Edital.id.desc()).all()
        disciplinas = session.query(models.Disciplina).order_by(models.Disciplina.nome).all()
        topicos = session.query(models.Topico).order_by(models.Topico.nome).all()
    finally:
        session.close()

    return editais, disciplinas, topicos


def show_questoes_view():
    st.title("Lançar Questões")
    st.info("Registre acertos e erros por tópico para alimentar o dashboard.")

    editais, disciplinas, topicos = load_questoes_options()

    with st.form("form_questoes", clear_on_submit=True):
        edital_options = ["-- Selecionar edital --"] + [f"{e.id} - {e.nome_concurso}" for e in editais]
        sel_edital = st.selectbox("Edital", edital_options, key="q_edital")

        selected_edital_id = None
        if sel_edital and sel_edital != "-- Selecionar edital --":
            selected_edital_id = int(sel_edital.split(" - ")[0])

        disciplinas_filtradas = [d for d in disciplinas if d.edital_id == selected_edital_id] if selected_edital_id else []
        disciplina_options = ["-- Selecionar disciplina --"] + [f"{d.id} - {d.nome}" for d in disciplinas_filtradas]
        sel_disciplina = st.selectbox("Disciplina", disciplina_options, key="q_disciplina")

        selected_disciplina_id = None
        if sel_disciplina and sel_disciplina != "-- Selecionar disciplina --":
            selected_disciplina_id = int(sel_disciplina.split(" - ")[0])

        topicos_filtrados = [t for t in topicos if t.disciplina_id == selected_disciplina_id] if selected_disciplina_id else []
        topico_options = ["-- Selecionar tópico --"] + [f"{t.id} - {t.nome}" for t in topicos_filtrados]
        sel_topico = st.selectbox("Tópico", topico_options, key="q_topico")

        selected_topico_id = None
        if sel_topico and sel_topico != "-- Selecionar tópico --":
            selected_topico_id = int(sel_topico.split(" - ")[0])

        acertos = st.number_input("Acertos", min_value=0, step=1, value=0)
        erros = st.number_input("Erros", min_value=0, step=1, value=0)

        submitted = st.form_submit_button("Salvar registro")

        if submitted:
            if not selected_topico_id:
                st.error("Selecione um edital → disciplina → tópico antes de salvar.")
            else:
                session = SessionLocal()
                try:
                    registro = models.QuestaoHistorico(
                        topico_id=selected_topico_id,
                        acertos=int(acertos),
                        erros=int(erros),
                    )
                    session.add(registro)
                    session.commit()
                    st.success("Registro salvo com sucesso.")
                    st.cache_data.clear()
                except Exception as exc:
                    session.rollback()
                    st.error(f"Não foi possível salvar o registro: {exc}")
                finally:
                    session.close()
