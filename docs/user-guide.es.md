# Cut List para IngeTrazo — guía de uso

*También en [English](user-guide.md) y [Português (Brasil)](user-guide.pt-BR.md).*
Para la versión 0.1.0, IngeTrazo 0.5.9.

Cut List convierte un modelo de mueble en la lista de piezas a cortar,
la envía al proveedor que corta tus tableros y dibuja los planos de corte
para tu propia sierra.

![Un plano de corte](images/cutting-diagram.png)

## 1. Instalar

1. Descarga `cutlist-0.1.0.zip` de la página de
   [Releases](https://github.com/ronaldogalves/cutlist-ingetrazo/releases)
   — o instala **Cut List** desde el gestor de extensiones de IngeTrazo.
2. A mano: en IngeTrazo, **Extensiones ▸ Abrir carpeta de complementos**,
   descomprime ahí, de modo que la carpeta tenga `cutlist/__init__.py`, y
   reinicia IngeTrazo.

Cut List aparece como una pestaña en el panel lateral y en **Extensiones
▸ Cut List**.

## 2. Cómo modelar para la lista de corte

- **Una pieza, un grupo o componente.** Cada tablero que cortas es un
  grupo o componente propio. Un mueble puede ser un grupo con sus piezas
  dentro; Cut List lee las piezas de dentro (los grupos más internos son
  las piezas).
- **Nombra las piezas.** El nombre es lo que ve el taller. Las piezas sin
  nombre aparecen como "Grupo #1", "Grupo #2"… y conservan su
  número.
- **Pinta las caras, no solo las piezas.** Cut List lee el modelo como lo
  pinta el carpintero: el material de las caras grandes es el tablero, un
  material distinto en una cara es un laminado o una chapa de madera, un
  material en un borde angosto es un canto.
- **Etiquetas** pueden dejar cosas fuera de la lista (paredes,
  electrodomésticos): usa el botón **Etiquetas** del panel.

## 3. Primer uso: qué entra en la lista

La primera vez que pulsas **Actualizar**, Cut List pregunta qué leer: la
selección o todo el modelo, también grupos simples o solo componentes, y
qué etiquetas dejar fuera. Marca "no volver a mostrar" y lo recuerda;
cámbialo luego en **Ajustes…**.

## 4. Materiales: di una vez qué es cada uno

Abre **Materiales…**. A la izquierda, todos los materiales hallados en
las piezas; a la derecha, qué es:

| Qué es | Significa |
|---|---|
| **Tablero** | el tablero que se corta (MDF, contrachapado, aglomerado…) |
| **Revestimiento** | laminado, HPL o chapa de madera pegada en una cara |
| **Canto** | canto en un borde |
| **Solo apariencia** | una textura que solo muestra algo (el borde del contrachapado) |
| **Ignorar** | no se corta: vidrio, herrajes, paredes |

Para un **tablero** también puedes definir:

- **Espesores** en que viene (p. ej. `15; 18`): una pieza modelada de
  14 mm en un tablero de 15 mm se marca *espesor fuera de lista*.
- **Tableros en que viene**: el tamaño real, no refilado. Un tamaño solo
  para algunos espesores va en la última columna (p. ej. `3; 6`).
  **Plantillas ▾** guarda tamaños con un nombre y los aplica a varios
  materiales a la vez — selecciónalos antes con Ctrl+clic.
- **Sierra** y **refilado**, cuando este tablero necesita otros que los
  predeterminados.
- **Sobremedida de corte**: toda pieza de este tablero se corta así de
  más grande, para llevarla a medida después. El modelo conserva la
  medida acabada.

Para un **canto**:

- **Espesor** y **ancho** (p. ej. 0,45 y 22 mm), y el **margen para el
  acabado** (2 mm por defecto, sumando los dos lados): una pieza más
  gruesa que ancho − margen se marca *canto demasiado angosto* — un canto
  de 22 mm sirve hasta 20 mm. Crea un canto por cada ancho que uses (22,
  30…) y pinta el correcto.
- **Sobremedida** por borde (lo que se refila después de pegar),
  **merma %** y el **largo del rollo** si lo compras en rollos — todo
  opcional.
- **Cortar el tablero más corto por el espesor del canto**: para cantos
  gruesos; la sierra recibe la medida menor, la lista conserva la
  acabada.

"Usar estos materiales también en mis otros modelos" (marcado) los pone
en tu biblioteca: todo modelo con un material del mismo nombre parte de
ella. En la lista, *mi biblioteca* y *solo en este modelo* dicen de dónde
viene cada configuración; *sin configurar* es un material por decidir.

## 5. Leer la lista

Las piezas se agrupan por **tablero y espesor**; las piezas iguales son
una línea con cantidad. Columnas: **Pieza** (la letra, la misma de los
planos de corte), nombre, cantidad, largo, ancho, espesor, **cantos**
(L1/L2 los largos, A1/A2 los cortos, vistos desde la cara 1), **caras**
(revestimientos) y **notas**.

**Revisar** lista lo que Cut List no adivina: piezas no rectangulares,
varios tableros unidos en un grupo, piezas sin material, acabados sin
configurar, espesores fuera de lista. Nada desaparece en silencio;
**Excluidas** lista lo que tú o un material dejaron fuera.

**Cantos** al final: los metros de cada canto a comprar, cuántos bordes
y los rollos, cuando se definen.

Haz clic en una línea para ver sus piezas resaltadas en el modelo.

## 6. Ajustes de la pieza

Clic derecho en una línea (o en piezas del modelo) ▸ **Ajustes de la
pieza…**: veta a lo largo o a lo ancho, si puede girar en el tablero,
dejarla fuera de la lista, invertir la cara 1, una nota, la **sobremedida
de corte** propia y los valores de sus campos personalizados. Cada cambio
es un paso de deshacer.

Los **campos personalizados** (cliente, ambiente…) se definen en
**Ajustes…**: un valor para el modelo, reglas por etiqueta o un valor por
pieza.

## 7. Exportar para un proveedor

**Exportar…** escribe la lista como la quiere tu proveedor. Un
**perfil** guarda todas las reglas: columnas y su orden, encabezado,
separador, codificación, unidades, redondeo, nombres de archivo. Perfiles
listos:

- **CorteCloud** — copia al portapapeles y pega en la ventana de
  importación de CorteCloud (o abre el archivo de Excel y pega desde ahí).
- **Leo Madeiras** — un CSV para la importación en la web de Leo.
- **Simple CSV** — para todo lo demás.

Cambia un perfil y **Guardar**, o **Guardar como…** uno nuevo;
**Importar…** acepta varios archivos de perfil a la vez, **Exportar
perfil…** comparte uno. La vista previa muestra exactamente lo que se
escribirá; los problemas (un código de proveedor que falta, un carácter
que la codificación del archivo no admite) se listan y detienen la
exportación hasta corregirlos. Desmarca tableros para dejarlos fuera de
esta exportación.
"También un archivo con los cantos a comprar" escribe los totales de
canto junto a la lista.

## 8. Planos de corte

**Planos…** distribuye cada tablero en sus hojas para una seccionadora o
sierra de mesa. Los tableros sin tamaño se preguntan una vez (Cancelar lo
detiene).

- **Tableros** a la izquierda, con hojas y cuánto se aprovecha.
- **La sierra**: primeros cortes a lo largo, a lo ancho (más fácil cuando
  cortas solo) o el mejor de los dos; 2, 3 o 4 etapas de corte; grosor de
  la sierra; refilado en los cuatro cantos o en dos. **Rehacer el plan**
  lo aplica.
- **Sobrantes del taller**: trozos que ya tienes, usados antes que los
  tableros enteros y nunca refilados.

En las hojas:

- **Pasa el ratón sobre una pieza**: su medida y los cortes que la
  liberan, cada uno con la distancia a poner en la guía; también se
  ilumina en el modelo. Las piezas seleccionadas en el modelo se iluminan
  en el plano.
- **Pasa el ratón sobre un corte**: su etapa, la distancia de la guía y
  su largo. Un primer corte cruza todo el tablero, así que cualquiera
  puede ir primero — para partir un tablero grande en dos antes del
  resto.
- **Clic derecho en una pieza**: cambiar su veta (todas las copias, o
  solo esta), permitir o prohibir girar, ajustes de la pieza, dejarla
  fuera de este plan, mostrarla en el modelo. Un cambio en la pieza es un
  paso de deshacer, y el plan se rehace para las mismas piezas.

## 9. Imprimir

Elige el papel (A4, Carta), el tamaño del texto (**Grande**, o
**Compacto** para menos páginas), si los tableros iguales aparecen una
vez (×n), una página de totales, las posiciones de los cortes en el
borde, los cortes en orden bajo cada tablero ("1 Longitudinal 645 · 2
Transversal 1982…": dónde poner la guía, desde el borde del trozo que se
corta); luego **PDF…** o **SVG…**. Cada página dice "Página n de N" con el
modelo, el tablero y la fecha, para poder reordenar en el taller las hojas
que se mezclen.

## 10. Etiquetas

**Etiquetas…** (en el panel, o en la ventana de los planos) hace una
etiqueta para cada pieza. Elige la hoja de etiquetas (hojas Pimaco y
Avery en A4 o Carta, o **Hoja personalizada…** con sus medidas) y
**Empezar en la etiqueta** en una hoja ya usada. Cada etiqueta lleva la
letra de la pieza, nombre y medida, material y espesor, el modelo y tus
campos personalizados, "3 de 4" y un pequeño dibujo con los bordes con
canto y la veta. Desde los planos, las etiquetas salen por tablero y
dicen de qué tablero sale cada pieza. **Contornear cada etiqueta**
imprime los marcos, para probar antes en papel común.

## 11. Guardar un plan

**Guardar plan…** guarda el plan en el modelo (se guarda con el archivo).
**Planes guardados ▾** lo reabre exactamente como era — aunque hoy la
distribución saliera distinta. Si el modelo cambió desde entonces, la
ventana dice qué piezas cambiaron de medida o ya no están, y **Rehacer el
plan para estas piezas** las distribuye de nuevo.

## 12. Bueno saber

- Las medidas en las ventanas se escriben en milímetros; la lista sigue
  las unidades del modelo, salvo lo definido en **Ajustes…**.
- La madera maciza se lista pero aún no se distribuye; los planos son
  para sierra, no para nesting de CNC.
- Los archivos `.skp` llegan a IngeTrazo sin su jerarquía de grupos, y
  grupos y componentes no se separan: revisa *Revisar*.
- Preguntas, errores y perfiles para otros proveedores:
  [github.com/ronaldogalves/cutlist-ingetrazo](https://github.com/ronaldogalves/cutlist-ingetrazo/issues).
