import streamlit as st
import pdfplumber
import io
import re
import pandas as pd
from sqlalchemy import func

from database import SessionLocal
import models


LEVEL_LABELS = ["Teoria", "Resumo", "Questões", "Revisão"]
LEVEL_MAP = {label: i + 1 for i, label in enumerate(LEVEL_LABELS)}


def extract_disciplinas_topicos_from_pdf(uploaded_file) -> list:
    """Tenta extrair disciplinas e tópicos de um PDF usando heurísticas simples.

    Retorna lista de dicts: {'disciplina': str, 'topico': str}
    """
    try:
        raw = uploaded_file.read()
        pdf = pdfplumber.open(io.BytesIO(raw))
        text = []
        for p in pdf.pages:
            try:
                t = p.extract_text()
            except Exception:
                t = None
            if t:
                text.append(t)
        pdf.close()
        full = "\n".join(text)
    except Exception:
        return []

    # Localizar ponto de início comum "conteúdo programático"
    m = re.search(r"conte[uú]do programar|conte[uú]do program[aá]tico|programa\s+de\s+conte[uú]do", full, re.IGNORECASE)
    if m:
        substr = full[m.end():]
    else:
        substr = full

    lines = [l.strip() for l in substr.splitlines() if l.strip()]

    results = []
    current_disciplina = None

    for line in lines:
        # Linha que parece ser título de disciplina (muitas letras maiúsculas, sem ponto final)
        if re.match(r'^[A-Z0-9\-\s\(\)\/\:]{3,}$', line) and len(line) <= 120:
            current_disciplina = line.title()
            continue

        # Linha com formato "Disciplina: tópicos..."
        if ":" in line and len(line.split(":")[0]) < 80:
            disc, rest = line.split(":", 1)
            current_disciplina = disc.strip().title()
            topics = re.split(r"[•\-;\n\t\u2022]|,", rest)
            for t in topics:
                t = t.strip()
                if t:
                    results.append({"disciplina": current_disciplina, "topico": t})
            continue

        # Bullet points ou linhas iniciando por números
        if re.match(r'^[\-•\*\d\)\.]', line) and current_disciplina:
            top = re.sub(r'^[\-•\*\d\)\.]\s*', '', line).strip()
            if top:
                results.append({"disciplina": current_disciplina, "topico": top})
            continue

        # Último recurso: se houver disciplina corrente, cada linha curta é tratado como tópico
        if current_disciplina and len(line) < 200:
            results.append({"disciplina": current_disciplina, "topico": line})

    return results


def show_edital_view():
    st.title("Edital Verticalizado")
    st.info("Carregue um PDF do conteúdo programático ou cadastre manualmente disciplinas e tópicos.")

    session = SessionLocal()
    try:
        editais = session.query(models.Edital).order_by(models.Edital.id.desc()).all()
        edital_options = ["-- Criar novo edital --"] + [f"{e.id} - {e.nome_concurso}" for e in editais]

        sel = st.selectbox("Selecionar Edital", edital_options)

        selected_edital = None
        if sel and sel != "-- Criar novo edital --":
            eid = int(sel.split(" - ")[0])
            selected_edital = session.query(models.Edital).get(eid)

        with st.expander("Criar novo edital"):
            nome = st.text_input("Nome do Concurso", key="ev_nome")
            banca = st.text_input("Banca", key="ev_banca")
            data = st.date_input("Data da Prova", key="ev_data")
            if st.button("Criar Edital", key="ev_criar"):
                novo = models.Edital(nome_concurso=nome, banca=banca, data_prova=data)
                session.add(novo)
                session.commit()
                st.success("Edital criado com sucesso. Selecione-o no menu acima.")

        uploaded = st.file_uploader("Carregar PDF do Conteúdo Programático", type=["pdf"])

        parsed_results = []
        df = pd.DataFrame(columns=["disciplina", "topico"])

        if uploaded is not None:
            with st.spinner("Extraindo texto do PDF..."):
                try:
                    parsed_results = extract_disciplinas_topicos_from_pdf(uploaded)
                except Exception as e:
                    parsed_results = []

            if parsed_results:
                df = pd.DataFrame(parsed_results)
                st.success(f"Foram detectados {len(df)} tópicos (heurística). Revise abaixo.")
            else:
                st.warning("Não foi possível extrair tópicos automaticamente. Cadastre manualmente abaixo.")
                df = pd.DataFrame(columns=["disciplina", "topico"])

        # Editor (sempre mostrar, preenchido ou em branco)
        st.markdown("#### Revisar / Editar Disciplinas e Tópicos")
        edited = st.data_editor(df, num_rows="dynamic", key="ev_data_editor")

        if st.button("Importar tópicos para o edital"):
            if selected_edital is None:
                st.error("Selecione ou crie um edital antes de importar.")
            else:
                # salvar disciplinas e tópicos
                rows = edited.to_dict(orient="records") if isinstance(edited, pd.DataFrame) else edited
                created = 0
                for r in rows:
                    disc_name = (r.get("disciplina") or "").strip()
                    top_name = (r.get("topico") or "").strip()
                    if not disc_name or not top_name:
                        continue
                    # localizar ou criar disciplina
                    disc = (
                        session.query(models.Disciplina)
                        .filter(func.lower(models.Disciplina.nome) == disc_name.lower(), models.Disciplina.edital_id == selected_edital.id)
                        .first()
                    )
                    if not disc:
                        disc = models.Disciplina(edital_id=selected_edital.id, nome=disc_name)
                        session.add(disc)
                        session.flush()
                    # verificar se tópico existe
                    exists = (
                        session.query(models.Topico)
                        .filter(models.Topico.disciplina_id == disc.id, func.lower(models.Topico.nome) == top_name.lower())
                        .first()
                    )
                    if not exists:
                        top = models.Topico(disciplina_id=disc.id, nome=top_name)
                        session.add(top)
                        created += 1
                session.commit()
                st.success(f"Importação finalizada. {created} tópicos criados.")

        # Exibir tópicos já cadastrados para o edital selecionado
        if selected_edital:
            st.markdown("---")
            st.markdown(f"### Tópicos cadastrados no edital: {selected_edital.nome_concurso}")
            topicos = (
                session.query(models.Topico)
                .join(models.Disciplina)
                .filter(models.Disciplina.edital_id == selected_edital.id)
                .order_by(models.Disciplina.nome, models.Topico.nome)
                .all()
            )

            if not topicos:
                st.info("Nenhum tópico cadastrado ainda para este edital.")
            else:
                with st.form("topicos_form"):
                    updates = []
                    for t in topicos:
                        col1, col2 = st.columns([4, 1])
                        col1.write(f"**{t.disciplina.nome}** — {t.nome}")
                        revisado = col2.checkbox("Revisado", value=bool(t.revisado), key=f"rev_{t.id}")
                        nivel_label = LEVEL_LABELS[t.nivel_dominio - 1] if 1 <= t.nivel_dominio <= 4 else LEVEL_LABELS[0]
                        nivel = col2.selectbox("Nível", LEVEL_LABELS, index=LEVEL_LABELS.index(nivel_label), key=f"lvl_{t.id}")
                        updates.append((t, revisado, nivel))

                    submitted = st.form_submit_button("Salvar alterações")
                    if submitted:
                        from sqlalchemy import func

                        changed = 0
                        for t, revisado, nivel in updates:
                            new_nivel = LEVEL_MAP.get(nivel, 1)
                            if t.revisado != revisado or t.nivel_dominio != new_nivel:
                                t.revisado = bool(revisado)
                                t.nivel_dominio = int(new_nivel)
                                session.add(t)
                                changed += 1
                        session.commit()
                        st.success(f"Salvas {changed} atualizações.")
    finally:
        session.close()
