import streamlit as st
from database import SessionLocal
import models
import pandas as pd
import plotly.express as px
from datetime import date
from sqlalchemy import func


@st.cache_data
def load_data():
    session = SessionLocal()
    try:
        editais = [
            {"id": e.id, "nome_concurso": e.nome_concurso, "data_prova": e.data_prova} for e in session.query(models.Edital).all()
        ]
        disciplinas = [
            {"id": d.id, "edital_id": d.edital_id, "nome": d.nome} for d in session.query(models.Disciplina).all()
        ]
        topicos = [
            {"id": t.id, "disciplina_id": t.disciplina_id, "nome": t.nome, "nivel_dominio": t.nivel_dominio, "revisado": t.revisado}
            for t in session.query(models.Topico).all()
        ]
        historico = [
            {"id": h.id, "topico_id": h.topico_id, "acertos": h.acertos, "erros": h.erros, "data_resolucao": h.data_resolucao}
            for h in session.query(models.QuestaoHistorico).all()
        ]
    finally:
        session.close()

    return (
        pd.DataFrame(editais),
        pd.DataFrame(disciplinas),
        pd.DataFrame(topicos),
        pd.DataFrame(historico),
    )


def show_dashboard_view():
    st.title("Dashboard")
    st.markdown("Visão de eficiência e inteligência de prova")

    df_editais, df_disciplinas, df_topicos, df_hist = load_data()

    # KPI 1: % do edital concluído (usar próximo edital se houver)
    pct_concluido = None
    dias_restantes = None
    if not df_editais.empty:
        today = date.today()
        df_editais['data_prova'] = pd.to_datetime(df_editais['data_prova']).dt.date
        future = df_editais[df_editais['data_prova'] >= today]
        if not future.empty:
            next_edital = future.loc[future['data_prova'].idxmin()]
        else:
            next_edital = df_editais.loc[df_editais['data_prova'].idxmax()]

        dias_restantes = (pd.to_datetime(next_edital['data_prova']).date() - today).days

        # calcular % concluído por tópicos revisados
        if not df_topicos.empty:
            # map disciplinas to edital
            df = df_topicos.merge(df_disciplinas[['id','edital_id']], left_on='disciplina_id', right_on='id', how='left', suffixes=('','_disc'))
            df = df[df['edital_id'] == next_edital['id']]
            total = len(df)
            if total > 0:
                concl = df['revisado'].astype(bool).sum()
                pct_concluido = int(round((concl / total) * 100))
            else:
                pct_concluido = 0
        else:
            pct_concluido = 0
    else:
        pct_concluido = 0

    # KPI 2: % de Acertos Global
    if not df_hist.empty:
        total_acertos = df_hist['acertos'].sum()
        total_erros = df_hist['erros'].sum()
        denom = total_acertos + total_erros
        pct_acertos = int(round((total_acertos / denom) * 100)) if denom > 0 else 0
    else:
        pct_acertos = 0

    # KPI 3: dias restantes (usar dias_restantes calculado)
    dias_display = dias_restantes if dias_restantes is not None else "—"

    c1, c2, c3 = st.columns(3)
    c1.metric("% do Edital Concluído", f"{pct_concluido}%")
    c2.metric("% de Acertos Global", f"{pct_acertos}%")
    c3.metric("Dias até a prova", dias_display)

    st.markdown("---")

    # Preparar dados para gráfico por disciplina
    if df_hist.empty or df_topicos.empty or df_disciplinas.empty:
        st.info("Dados insuficientes para gerar gráficos. Cadastre tópicos e registros de questões.")
        return

    # juntar historico -> topico -> disciplina
    df_th = df_hist.groupby('topico_id').agg({'acertos':'sum','erros':'sum'}).reset_index()
    df_t = df_topicos[['id','disciplina_id','nome']].rename(columns={'id':'topico_id','nome':'topico'})
    df_td = df_t.merge(df_th, on='topico_id', how='left').fillna(0)
    df_disc = df_disciplinas[['id','nome']].rename(columns={'id':'disciplina_id','nome':'disciplina'})
    df_full = df_td.merge(df_disc, on='disciplina_id', how='left')

    # percentuais por disciplina
    disc_group = df_full.groupby('disciplina').agg({'acertos':'sum','erros':'sum'}).reset_index()
    disc_group['percent_acertos'] = disc_group.apply(lambda r: (r['acertos'] / (r['acertos']+r['erros']))*100 if (r['acertos']+r['erros'])>0 else 0, axis=1)
    disc_group = disc_group.sort_values('percent_acertos', ascending=True)

    fig_bar = px.bar(disc_group, x='percent_acertos', y='disciplina', orientation='h', labels={'percent_acertos':'% Acertos','disciplina':'Disciplina'}, text=disc_group['percent_acertos'].round(1))
    fig_bar.update_layout(height=400)
    st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("---")

    # Heatmap simulado: cruzar nivel_dominio com erros por tópico
    df_errors = df_hist.groupby('topico_id').agg({'erros':'sum'}).reset_index()
    df_topics_errors = df_topicos[['id','nivel_dominio','nome']].rename(columns={'id':'topico_id','nome':'topico'}).merge(df_errors, on='topico_id', how='left').fillna(0)

    # criar buckets de erros
    bins = [-1,0,1,3,6,9999]
    labels = ['0','1','2-3','4-6','7+']
    df_topics_errors['erro_bucket'] = pd.cut(df_topics_errors['erros'], bins=bins, labels=labels)

    pivot = df_topics_errors.groupby(['nivel_dominio','erro_bucket']).size().unstack(fill_value=0).reindex(index=[1,2,3,4])

    # garantir colunas na ordem
    pivot = pivot[labels]

    z = pivot.values
    fig_heat = px.imshow(z, x=labels, y=["Nível 1","Nível 2","Nível 3","Nível 4"], color_continuous_scale='RdYlGn_r', labels={'x':'Erros (bucket)','y':'Nível de domínio','color':'Quantidade de tópicos'})
    fig_heat.update_layout(height=400)
    st.subheader("Mapa de Calor: Prioridade de Revisão")
    st.plotly_chart(fig_heat, use_container_width=True)
