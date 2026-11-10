"""Página «🔒 Privacidad»: política de tratamiento de datos (Ley 1581 de 2012, Colombia)."""

from __future__ import annotations

import streamlit as st

from paddock.interfaz.componentes import recursos


def render() -> None:
    aj = recursos.contenedor().ajustes
    st.subheader("🔒 Política de tratamiento de datos personales")
    st.caption("Versión 1.0 · Ley Estatutaria 1581 de 2012 y Decreto 1377 de 2013 (compilado en el Decreto 1074 de 2015).")
    st.markdown(f"""
**Responsable del tratamiento.** El operador de Paddock Global (proyecto académico). Contacto:
`privacidad@midominio.com` *(sustituye este marcador por el correo real antes de publicar)*.

**Qué datos tratamos**

- **Cuenta:** correo, nombre visible y una huella de tu contraseña (argon2id). Nunca guardamos la contraseña.
- **Opiniones:** el texto que escribes, la carrera, la edición, la fecha y la clasificación automática.
- **Seguridad:** registros de auditoría (inicio y cierre de sesión, cambios de rol, revisiones) con la
  dirección IP **convertida en un código irreversible** (hash con sal). No guardamos la IP en claro.

**Para qué:** mostrar y analizar en conjunto la percepción de la comunidad sobre las carreras, moderar
contenido, proteger la plataforma contra abusos y cumplir obligaciones legales. No vendemos datos ni
hacemos publicidad.

**Encargado externo: clasificación con IA.** En producción, el texto de cada opinión se envía a
**Google Gemini** para clasificar su sentimiento (proveedor configurado ahora: `{aj.LLM_PROVIDER}`).
Con el nivel gratuito de la API, **Google puede usar los datos para mejorar sus productos**. No escribas
datos personales tuyos ni de terceros en las opiniones. En el modo de desarrollo con Ollama, el texto
no sale del equipo.

**Tus derechos (artículo 8 de la Ley 1581):** conocer, actualizar y rectificar tus datos; pedir prueba
de la autorización; ser informado del uso; revocar la autorización y pedir la supresión; y presentar
quejas ante la Superintendencia de Industria y Comercio. Desde **👤 Mi cuenta** puedes **exportar tus
datos** (JSON) y **eliminar tu cuenta**: tus opiniones se conservan de forma anónima, sin vínculo
contigo, porque forman parte de las estadísticas agregadas.

**Conservación:** mientras la cuenta exista; los registros de auditoría, hasta 12 meses; las copias de
seguridad, 14 días.

**Seguridad:** conexión cifrada (HTTPS), contraseñas con argon2id, control de acceso por rol, límites de
uso y base de datos no expuesta a internet.

**Datos sensibles y menores:** la plataforma no solicita datos sensibles. Si eres menor de edad, usa la
app con autorización de tu representante legal.
""")


render()
