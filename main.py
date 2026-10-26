from pathlib import Path

import numpy as np
import pyvista as pv
import streamlit as st
import streamlit.components.v1 as components


st.set_page_config(
    page_title="Esqueleto T-Rex",
    page_icon="🦖",
    layout="wide",
)

CARPETA_MODELOS = Path(__file__).resolve().parent / "models"

# nombre de archivo, nombre visible, posición manual, dirección de salida
HUESOS = [
    ("TRex_Skull", "Cráneo",
     (0, 1.8, 2.3), (0, 2, 3)),

    ("TRex_Jaw", "Mandíbula",
     (0, 1.3, 2.4), (0, -2, 3)),

    ("TRex_Vertebrae_Neck", "Vértebras del cuello",
     (0, 1.4, 1.3), (0, 2, 2)),

    ("scapulas", "Escápulas",
     (0, 1.3, 0.8), (0, 2, 1)),

    ("TRex_Arms", "Brazos",
     (0, 0.8, 1.0), (0, -1, 3)),

    ("TRex_Vertebrae_Dorsal_A", "Vértebras dorsales A",
     (0, 1.2, 0.3), (0, 1, 0)),

    ("TRex_Vertebrae_Dorsal_B", "Vértebras dorsales B",
     (0, 1.0, -0.4), (0, 0, -1)),

    ("rib_cage", "Caja torácica",
     (0, 1.0, 0.2), (3, 1, 0)),

    ("TRex_Hip_Top", "Cadera superior",
     (0, 1.0, -1.0), (0, 2, -2)),

    ("TRex_Hip_Bottom", "Cadera inferior",
     (0, 0.7, -1.0), (0, -1, -2)),

    ("femur_R", "Fémur derecho",
     (0.4, 0.5, -0.8), (2, 0, -1)),

    ("tibia_L", "Tibia izquierda",
     (-0.4, -0.1, -0.7), (-2, -2, -1)),

    ("tibia_R", "Tibia derecha",
     (0.4, -0.1, -0.7), (2, -2, -1)),

    ("foot_L", "Pie izquierdo",
     (-0.5, -0.8, -0.6), (-2, -3, -1)),

    ("foot_R", "Pie derecho",
     (0.5, -0.8, -0.6), (2, -3, -1)),

    ("tail_A", "Cola A",
     (0, 0.8, -1.7), (-1, 0, -2)),

    ("tail_B", "Cola B",
     (0, 0.7, -2.4), (1, -1, -3)),

    ("tail_C", "Cola C",
     (0, 0.5, -3.1), (-1, -1, -4)),

    ("tail_D", "Cola D",
     (0, 0.4, -3.8), (2, -2, -5)),
]


@st.cache_data(show_spinner=False)
def cargar_malla(ruta, fecha_modificacion):
    # La fecha permite invalidar la caché si cambias el archivo.
    return pv.read(ruta)


def cambiar_nivel(valor):
    st.session_state["nivel"] = valor


st.title("Explorador del esqueleto del T-Rex")
st.caption("Arma el esqueleto, separa sus piezas y destaca cada hueso.")

if "nivel" not in st.session_state:
    st.session_state["nivel"] = 0.0

with st.sidebar:
    st.header("Controles")

    modo = st.radio(
        "¿Cómo están guardadas tus piezas?",
        [
            "Ya están armadas en coordenadas comunes",
            "Quiero colocarlas con posiciones manuales",
        ],
    )

    escala = st.number_input(
        "Escala de las mallas",
        min_value=0.000001,
        value=0.015,
        step=0.001,
        format="%.6f",
        help=(
            "Multiplica las coordenadas de todas las piezas. "
            "Prueba 1.0 si tu modelo ya tiene el tamaño correcto."
        ),
    )

    distancia = st.number_input(
        "Factor de separación",
        min_value=0.0,
        value=2.0,
        step=0.25,
    )

    columna_a, columna_b = st.columns(2)

    columna_a.button(
        "Armar",
        on_click=cambiar_nivel,
        args=(0.0,),
        use_container_width=True,
    )

    columna_b.button(
        "Desarmar",
        on_click=cambiar_nivel,
        args=(1.0,),
        use_container_width=True,
    )

    nivel = st.slider(
        "Nivel de despiece",
        min_value=0.0,
        max_value=1.0,
        step=0.05,
        key="nivel",
    )

    mostrar_bordes = st.checkbox("Mostrar bordes", value=False)


disponibles = []
faltantes = []

for archivo, nombre, home, direccion in HUESOS:
    ruta = CARPETA_MODELOS / f"{archivo}.stl"

    if ruta.is_file():
        disponibles.append((ruta, nombre, home, direccion))
    else:
        faltantes.append(ruta.name)

if faltantes:
    with st.expander(f"Archivos no encontrados: {len(faltantes)}"):
        st.write("\n".join(f"- {nombre}" for nombre in faltantes))

if not disponibles:
    st.error(
        "No encontré huesos. Crea la carpeta 'models' junto a main.py "
        "y coloca allí tus archivos STL con los nombres indicados."
    )
    st.stop()

with st.sidebar:
    destacado = st.selectbox(
        "Destacar hueso",
        ["Ninguno"] + [item[1] for item in disponibles],
    )

    solo_destacado = st.checkbox(
        "Mostrar únicamente el hueso destacado",
        disabled=destacado == "Ninguno",
    )

st.caption(
    f"Piezas disponibles: {len(disponibles)} · "
    f"Despiece: {nivel:.0%}"
)

plotter = pv.Plotter(
    off_screen=True,
    window_size=(1100, 700),
)

try:
    plotter.set_background("#19202a")
    cargados = 0

    for ruta, nombre, home, direccion in disponibles:
        if (
            solo_destacado
            and destacado != "Ninguno"
            and nombre != destacado
        ):
            continue

        try:
            original = cargar_malla(
                str(ruta),
                ruta.stat().st_mtime_ns,
            )

            # Copia independiente para no acumular desplazamientos.
            malla = original.copy(deep=True)

            if malla.n_points == 0:
                st.warning(f"La malla de {nombre} está vacía.")
                continue

            puntos = np.asarray(malla.points, dtype=float).copy()

            if modo == "Quiero colocarlas con posiciones manuales":
                # Centramos cada pieza y la llevamos a su posición home.
                puntos -= np.asarray(malla.center)
                puntos *= escala
                puntos += np.asarray(home)
            else:
                # Conservamos la colocación relativa exportada.
                puntos *= escala

            malla.points = puntos

            desplazamiento = (
                np.asarray(direccion, dtype=float)
                * distancia
                * nivel
            )

            malla.translate(
                desplazamiento,
                inplace=True,
            )

            plotter.add_mesh(
                malla,
                name=nombre,
                color="#ffad42" if nombre == destacado else "#ebe6d7",
                smooth_shading=True,
                show_edges=mostrar_bordes,
            )

            cargados += 1

        except Exception as error:
            st.warning(f"No pude cargar {ruta.name}: {error}")

    if cargados == 0:
        st.error("No se pudo mostrar ninguna pieza.")
    else:
        plotter.view_isometric()
        plotter.reset_camera()

        if hasattr(plotter, "trame"):
            html = plotter.trame.export_html(filename=None)
        else:
            html = plotter.export_html(filename=None)

        components.html(
            html.getvalue(),
            height=720,
            scrolling=False,
        )

finally:
    plotter.close()