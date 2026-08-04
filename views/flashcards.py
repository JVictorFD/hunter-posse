import streamlit as st
from database import SessionLocal
import models
import pandas as pd
import io
import html


def show_flashcards_view():
    st.title("Exportar Flashcards")
    st.info("Crie e exporte flashcards compatíveis com AnkiDroid.")

    session = SessionLocal()
    try:
        # Seleção de edital -> disciplina -> tópico
        editais = session.query(models.Edital).order_by(models.Edital.id.desc()).all()
        edital_map = {str(e.id): e for e in editais}
        edital_options = ["-- Selecionar edital --"] + [f"{e.id} - {e.nome_concurso}" for e in editais]
        sel_edital = st.selectbox("Edital", edital_options, key="fc_edital")

        selected_edital = None
        if sel_edital and sel_edital != "-- Selecionar edital --":
            eid = int(sel_edital.split(" - ")[0])
            selected_edital = session.query(models.Edital).get(eid)

        disciplinas = []
        if selected_edital:
            disciplinas = (
                session.query(models.Disciplina).filter(models.Disciplina.edital_id == selected_edital.id).order_by(models.Disciplina.nome).all()
            )

        disciplina_options = ["-- Selecionar disciplina --"] + [f"{d.id} - {d.nome}" for d in disciplinas]
        sel_disc = st.selectbox("Disciplina", disciplina_options, key="fc_disc")

        selected_disc = None
        if sel_disc and sel_disc != "-- Selecionar disciplina --":
            did = int(sel_disc.split(" - ")[0])
            selected_disc = session.query(models.Disciplina).get(did)

        topicos = []
        if selected_disc:
            topicos = session.query(models.Topico).filter(models.Topico.disciplina_id == selected_disc.id).order_by(models.Topico.nome).all()

        topico_options = ["-- Selecionar tópico --"] + [f"{t.id} - {t.nome}" for t in topicos]
        sel_top = st.selectbox("Tópico", topico_options, key="fc_top")

        selected_top = None
        if sel_top and sel_top != "-- Selecionar tópico --":
            tid = int(sel_top.split(" - ")[0])
            selected_top = session.query(models.Topico).get(tid)

        st.markdown("#### Criar Flashcard")
        frente = st.text_area("Frente (Pergunta / Conceito)")
        verso = st.text_area("Verso (Resposta / Lei)")

        if st.button("Salvar Flashcard"):
            if not selected_top:
                st.error("Selecione um edital → disciplina → tópico antes de salvar.")
            elif not frente or not verso:
                st.error("Preencha frente e verso do flashcard.")
            else:
                # tags: disciplina e tópico sem espaços
                disc_tag = selected_disc.nome.replace(" ", "_") if selected_disc else ""
                top_tag = selected_top.nome.replace(" ", "_") if selected_top else ""
                tags = f"{disc_tag} {top_tag}".strip()
                fc = models.Flashcard(topico_id=selected_top.id, frente=frente, verso=verso, tags=tags)
                session.add(fc)
                session.commit()
                st.success("Flashcard salvo com sucesso.")

        st.markdown("---")
        st.markdown("#### Exportar por Disciplina")
        # Export: escolher disciplina global (não necessariamente do edital selecionado)
        all_disc = session.query(models.Disciplina).order_by(models.Disciplina.nome).all()
        all_options = ["-- Selecionar disciplina --"] + [f"{d.id} - {d.nome}" for d in all_disc]
        sel_export = st.selectbox("Disciplina para exportar", all_options, key="fc_export_disc")
        sep = st.radio("Separador CSV", options=[",", ";"], index=0, horizontal=True)

        if st.button("Gerar CSV para AnkiDroid"):
            if not sel_export or sel_export == "-- Selecionar disciplina --":
                st.error("Selecione uma disciplina para exportar.")
            else:
                did = int(sel_export.split(" - ")[0])
                disc = session.query(models.Disciplina).get(did)
                # coletar flashcards para tópicos dessa disciplina
                tps = session.query(models.Topico).filter(models.Topico.disciplina_id == disc.id).all()
                tp_ids = [t.id for t in tps]
                fcs = session.query(models.Flashcard).filter(models.Flashcard.topico_id.in_(tp_ids)).all()
                if not fcs:
                    st.info("Nenhum flashcard encontrado para esta disciplina.")
                else:
                    rows = []
                    for f in fcs:
                        topic = session.query(models.Topico).get(f.topico_id)
                        disc_name = disc.nome
                        topic_name = topic.nome if topic else ""
                        # tags: disciplina and topic without spaces
                        tag_disc = disc_name.replace(" ", "_")
                        tag_topic = topic_name.replace(" ", "_")
                        tags_field = f"{tag_disc} {tag_topic}".strip()
                        rows.append({"frente": f.frente, "verso": f.verso, "tags": tags_field})

                    df = pd.DataFrame(rows)[["frente", "verso", "tags"]]
                    csv_bytes = df.to_csv(sep=sep, header=False, index=False).encode("utf-8")
                    filename = f"flashcards_{disc.nome.replace(' ','_')}.csv"
                    st.download_button("Baixar CSV (AnkiDroid)", data=csv_bytes, file_name=filename, mime="text/csv")
    finally:
        session.close()
