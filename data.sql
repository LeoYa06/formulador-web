--
-- PostgreSQL database dump
--

\restrict ocR3t8cjzOk8p5ReVGjF54tdpJCcn7ptjhu3fzx8DfgCVUjxXzzsPShvJWNvRnb

-- Dumped from database version 17.6 (Debian 17.6-1.pgdg12+1)
-- Dumped by pg_dump version 17.6

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Data for Name: base_ingredients; Type: TABLE DATA; Schema: public; Owner: formulador_db_user
--

COPY "public"."base_ingredients" ("id", "name", "protein_percent", "fat_percent", "water_percent", "Ve_Protein_Percent", "notes", "water_retention_factor", "min_usage_percent", "max_usage_percent", "precio_por_kg", "categoria") FROM stdin;
2	Agua	\N	\N	100	\N	\N	\N	\N	\N	\N	Agua/Hielo
3	Ajo en Polvo	\N	\N	\N	\N	\N	\N	\N	\N	2	Condimento/Aditivo
8	Annatto	\N	\N	\N	\N	\N	\N	\N	\N	5	Colorante
9	Carmin de Cochinilla	\N	\N	\N	\N	\N	\N	\N	\N	12	Colorante
10	Carne de Cerdo	20	5	75	\N	\N	\N	\N	\N	2	Cárnico
11	Carne de Pollo	20	3	73	\N	\N	\N	\N	\N	1.5	Cárnico
12	Carragenina	\N	\N	\N	\N	\N	10	\N	\N	10	Retenedor/No Cárnico
14	Comino	\N	\N	\N	\N	\N	\N	\N	\N	8	Condimento/Aditivo
15	Cuero de Cerdo	35	8	57	\N	\N	\N	\N	\N	1.1	Cárnico
18	Grasa de Cerdo	11	29	60	\N	\N	\N	\N	\N	0.5	Cárnico
19	Harina de Arroz	\N	\N	\N	\N	\N	2	\N	\N	\N	Retenedor/No Cárnico
20	Harina de Trigo	\N	\N	\N	\N	\N	1.5	\N	\N	0.3	Retenedor/No Cárnico
21	Humo Liquido	\N	\N	\N	\N	\N	\N	\N	\N	10	Condimento/Aditivo
22	Nitrito de Sodio	\N	\N	\N	\N	\N	\N	\N	\N	3	Retenedor/No Cárnico
23	Pimienta Negra	\N	\N	\N	\N	\N	\N	\N	\N	5	Condimento/Aditivo
24	Proteina de Soya	90	0.8	7	\N	\N	\N	\N	\N	5	Retenedor/No Cárnico
26	Sal	\N	\N	\N	\N	\N	\N	\N	\N	0.25	Condimento/Aditivo
27	Fosfatos	\N	\N	\N	\N	\N	\N	\N	\N	2	Condimento/Aditivo
25	Carne de Res 80/20	18	5	72	\N	\N	\N	\N	\N	2.3	Cárnico
4	Almidon de Maiz	\N	\N	\N	\N	\N	4	\N	\N	2	Retenedor/No Cárnico
5	Almidon de Trigo	\N	\N	\N	\N	\N	3	\N	\N	3	Retenedor/No Cárnico
13	CDM	12	24	64	\N	\N	\N	\N	\N	1.1	Cárnico
16	Fecula de Papa	\N	\N	\N	\N	\N	8	\N	\N	3	Retenedor/No Cárnico
17	Fecula de Yuca	\N	\N	\N	\N	\N	6	\N	\N	2.5	Retenedor/No Cárnico
32	fosfato	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N
34	eritorbato	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N
36	carne de res	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N
\.


--
-- Data for Name: bibliografia; Type: TABLE DATA; Schema: public; Owner: formulador_db_user
--

COPY "public"."bibliografia" ("id", "titulo", "tipo", "contenido") FROM stdin;
1	Clasificación de Ingredientes en Productos Cárnicos	Referencia Teorica	1. Materia Prima Cárnica Estos son los componentes principales derivados de animales, que constituyen la base de los embutidos y fiambres . ◦ Carnes: Principalmente de porcino y vacuno, aunque también se utilizan otras especies como aves y caza . La carne puede ser picada o no. Para productos cárnicos, la carne debe ser de animales sanos, bien nutridos y haber reposado adecuadamente. Las características de la carne (como el pH, idealmente entre 5.4-5.8 para productos crudos) son cruciales para la calidad final, incluyendo la capacidad de retención de agua y la resistencia al ataque microbiano. La carne de cerdo es valorada por su sabor y textura, siendo preferible la magra y firme . ◦ Grasas: Un componente fundamental que influye en la textura, sabor, y jugosidad del embutido . Puede estar infiltrada en la carne o adicionada como tocino o cortezas. Las grasas deben ser duras para evitar el enranciamiento. Se distinguen grasas orgánicas (como la de riñón o vísceras) y grasas de los tejidos (dorsal, de pierna, de papada), estas últimas más resistentes al corte y usadas en embutidos. El contenido de grasa en la carne puede variar y se clasifica en magra (<10%), semigrasa (10-30%), y grasa (>30%). La grasa intramuscular, conocida como "marmolado" en bovinos y "veteado" en porcinos, es la última en depositarse y es clave para el sabor y la terneza . ◦ Vísceras y Despojos: Partes comestibles del animal como tripa, bazo, garganta, corazón, encéfalo, estómago, hígado, lengua, pulmones y riñones. Son ricos en vitaminas y se utilizan frescos en la preparación de ciertos embutidos . ◦ Sangre: Empleada como materia prima en algunos embutidos, como las morcillas . 2. Retenedores / Aglutinantes / Espesantes / Estabilizantes / Gelificantes Estos ingredientes se añaden para mejorar la consistencia, la capacidad de retención de agua, y la estabilidad de la mezcla . ◦ Almidones y Féculas: Proceden de harinas de trigo, maíz, arroz, yuca o papa . Actúan como espesantes, conservantes y estabilizadores, mejorando la consistencia de la mezcla y activando agentes de maduración. También ayudan a retener grandes cantidades de agua y a emulsionar la grasa, lo que permite economizar costos. Un exceso puede endurecer la textura . ◦ Proteínas: Incluyen proteínas de soya o de leche, y se añaden para retener agua y mejorar la mordida y estabilidad de la emulsión . Las proteínas contribuyen a la formación de geles y emulsiones en los alimentos . ◦ Gelatinas: Se utilizan en la composición de los fiambres industriales . ◦ Alginatos de sodio: Polisacáridos de algas que forman geles, uniendo la mezcla de carne y previniendo la pérdida de jugo . ◦ Gomas vegetales: Como los carragenes, goma guar y goma garrofín, se usan como espesantes o gelificantes en diversos productos . ◦ Otros Aglutinantes: Sémola de cebada y trigo, harina de soya y huevos también se mencionan como aglutinantes . 3. Condimentos y Especias Se utilizan para conferir características sensoriales específicas (sabor, aroma) y, en algunos casos, propiedades antioxidantes a los productos . ◦ Sal Común: Es el ingrediente no cárnico más utilizado. Contribuye al sabor, actúa como conservante (reduciendo la actividad de agua) y favorece la solubilización de proteínas, mejorando la ligazón de las materias primas y las propiedades emulsionantes . ◦ Especias Naturales: Se añaden enteras, quebradas o molidas. Ejemplos incluyen pimienta, comino, ajo, cebolla, orégano, pimentón, canela, clavo de olor, coriandro, nuez moscada, anís, hinojo, tomillo, romero, perejil, cilantro, eneldo, estragón . Algunas, como pimienta, tomillo, romero o ajo, también tienen propiedades antioxidantes . ◦ Hierbas Aromáticas: También contribuyen al sabor y aroma . ◦ Productos Vegetales no Especias: Cebolla, arroz, miga de pan, patata, etc., se pueden incorporar en algunos embutidos . 4. Aditivos (General) Son sustancias que se añaden a los alimentos para modificar sus características técnicas de elaboración, conservación o uso, sin ser consumidos como alimentos por sí mismos . Deben estar autorizados por la legislación alimentaria y declarados en el etiquetado . ◦ Propósitos Generales: Optimizar recursos, aumentar la vida útil, resaltar características sensoriales (color, sabor, aroma, textura), agregar textura o mejorar la apariencia general . No deben usarse para enmascarar defectos ni reducir el valor nutritivo . 5. Conservantes Sustancias que prolongan la vida útil de los alimentos al impedir o retardar el deterioro causado por microorganismos . ◦ Nitritos y Nitratos (E-249 a E-252): Muy frecuentes en embutidos y fiambres . Actúan como antimicrobianos (protegen contra Clostridium botulinum), mejoran el enrojecimiento y la conservación, y proporcionan el color rojo característico a los embutidos curados, además de sabor y aroma. Su uso ha sido cuestionado por la formación de nitrosaminas, que son sustancias tóxicas, especialmente en presencia de un medio ácido (estómago) o altas temperaturas (fritura, barbacoa, curación, salazón) . ◦ Sulfitos (E-220 a E-228): Se usan para mejorar el aspecto visual de la carne (color rojo) y prolongar su frescura, actuando como conservantes antioxidantes . Son considerados alérgenos . ◦ Ácido sórbico y sus sales, ácido benzoico y sus sales, ácido propiónico y sus sales: Otros conservantes comunes que actúan sobre tipos específicos de microorganismos y pH . ◦ Lactato: Se utiliza como conservante . 6. Colorantes Se adicionan para mejorar el aspecto visual o para recuperar el color perdido durante el procesamiento de los alimentos . ◦ Naturales: Pueden derivar de vegetales (cúrcuma, achiote, clorofila de albahaca/espinaca, espirulina, té verde matcha, flor de Jamaica, zanahoria, betarraga), animales (carmín), o minerales (dióxido de titanio) . Ejemplos incluyen curcumina, carotenoides, xantofilas, betalaínas . ◦ Sintéticos: Moléculas nuevas o síntesis de moléculas naturales . Ejemplos: tartrazina, amarillo ocaso, amaranto, rojo 40, ponceau 4R, indigotina, azul brillante, azul patente, negro brillante . ◦ Reacción de Maillard: Un complejo conjunto de reacciones químicas entre azúcares reductores y aminoácidos o proteínas, que ocurre durante el calentamiento o almacenamiento prolongado de los alimentos . Es responsable del color marrón (melanoidinas) y de una gran variedad de compuestos aromáticos y de sabor (como el "sabor a carne asada"). Se diferencia de la caramelización en que esta última es una descomposición térmica solo de azúcares . 7. Aromatizantes y Saborizantes / Potenciadores del Sabor Sustancias o mezclas que proporcionan o refuerzan el aroma y/o el sabor de los alimentos . ◦ Aromatizantes y Saborizantes: Pueden ser naturales o sintéticos . Los naturales se extraen de especias, frutas, verduras, levaduras, hierbas, productos lácteos, carnes, aves, mariscos y huevos. Se buscan para dar un sabor casero y natural . ◦ Potenciadores del Sabor: Resaltan o realzan el sabor y/o aroma de un alimento sin tener sabor por sí mismos . ▪ Glutamato Monosódico: Sal del ácido glutámico, intensifica los sabores salados, actuando en las papilas gustativas . ▪ Proteínas hidrolizadas vegetales y animales, hidrolizados de levadura: También son potenciadores del sabor . ▪ Maltol y Etil Maltol: Usados como resaltadores de sabor dulce . ◦ Humos Naturales Condensados: Se obtienen de la quema de maderas duras no resinosas y se utilizan para dar sabor ahumado . Además de estos, otros aditivos como los acidulantes (ácido acético, láctico, ascórbico, cítrico, fosfórico) regulan la acidez, inhiben el crecimiento microbiano, actúan como saborizantes y previenen la oxidación . Los edulcorantes (sacarina, ciclamato, aspartamo, acelsulfame-K) se usan para endulzar sin aportar calorías, o en productos bajos en calorías.
2	Clasificación de la Carne por su Contenido Graso	Articulo Web	Clasificación de la Carne por su Contenido Graso Las carnes se pueden clasificar según su contenido de grasa : • Canales de animales magros: Se caracterizan por tener un bajo contenido de grasa adherida a la carne, resultado de la selección genética para reducir la obesidad en la población y satisfacer la demanda de productos con menos grasa . Una carne magra se define generalmente como aquella con menos del 10% de grasa . • Canales de animales semigrasos: Presentan un contenido de grasa intermedio. Esta característica busca mejorar el sabor de la carne a través de la grasa infiltrada en las fibras musculares, conocida como "marmóreo" en bovinos y "veteado" en porcinos, que se logra mediante el mejoramiento genético y cruce de razas . Se clasifican con un contenido de grasa entre el 10% y el 30% . • Canales de animales grasos: Son las más tradicionales y provienen de animales con desbalances nutricionales que llevan a grandes cantidades de grasa corporal. Aunque actualmente son menos apetecidas por su relación con problemas cardiovasculares, persisten en productos tradicionales como el cerdo ibérico para la elaboración de jamón . Una carne con grasa se define como aquella con más del 30% de grasa . En la industria cárnica, las proporciones de carne magra y grasa suelen indicarse con dos números, donde el primero representa el porcentaje de carne y el segundo el de grasa . Ejemplos de estas clasificaciones incluyen : • Carne de res 80/20 (80% carne magra, 20% grasa) . • Carne de res 90/10 (90% carne magra, 10% grasa) . • Carne de cerdo 70/30 (70% carne magra, 30% grasa) . • Carne de cerdo 90/10 (90% carne magra, 10% grasa) . Es importante destacar que, al mezclar diferentes tipos de carne con distintos porcentajes de grasa, se puede obtener una proporción deseada. Por ejemplo, al mezclar 20 kg de carne 80/20 y 30 kg de carne 90/10, se obtienen 50 kg de una mezcla con un 26% de grasa, aproximándose a una carne 75/25 . Además del porcentaje de grasa total, las fuentes también mencionan que la grasa intramuscular es el único tipo de grasa que no se puede retirar del plato al momento del consumo y que influye en la terneza, jugosidad, palatabilidad y sabor de la carne . En bovinos se denomina "marmolado" y en porcinos "veteado" . Algunos cortes de carne de cerdo, como el lomo, solomillo y paletilla, pueden considerarse parte de una alimentación cardiosaludable a pesar de ser carne roja . Carne Deshuesada Mecánicamente (CDM) o Pasta de Ave Mecánicamente Deshuesada La "pasta de ave mecánicamente deshuesada" es un ingrediente que se utiliza en la elaboración de batidos cárnicos . En una formulación de salchicha, se menciona el uso de "Pasta de Pollo" , que es otro ejemplo de carne procesada mecánicamente. Estos ingredientes no cárnicos o preparados, como los almidones, gelatinas y féculas, se añaden a los fiambres industriales y preparados cárnicos para aumentar el volumen y peso del producto final, lo que tiene una motivación económica . Su uso en productos procesados como las salchichas es común, donde la carne suele ser reemplazada por soya, almidones y grasas saturadas, además de otros aditivos.
3	Resumen Codex Alimentario	Normativa	El Comité del Codex sobre Productos Cárnicos Elaborados (CCPMPP), bajo el amparo de la FAO/OMS, tenía como mandato elaborar normas mundiales para productos cárnicos elaborados, incluyendo la carne envasada para la venta al por menor y productos de carne de aves de corral. El Codex Alimentarius, o Código Alimentario, es un referente internacional para la regulación de aditivos, y aunque las fuentes no siempre especifican directamente las "dosis del Codex" para cada aditivo, sí mencionan las directrices y normas técnicas nacionales (NTC) que regulan su uso, las cuales suelen alinearse con los estándares internacionales . A continuación, se presenta un resumen de los aditivos y sus funciones, así como las dosis o rangos de uso mencionados en las fuentes: • Nitritos y Nitratos (Sales Nitrificantes): ◦ Usos: Son conservantes inorgánicos utilizados regularmente en productos cárnicos por su efecto antimicrobiano, especialmente contra Clostridium botulinum, inhibiendo la germinación de sus esporas y la formación de neurotoxinas. También inhiben otros microorganismos patógenos como S. aureus y Cl. Perfringens . Son responsables del desarrollo y estabilización del color rosado-rojizo en productos curados, aportan un sabor y aroma característico, y tienen un efecto antioxidante que modula los sabores rancios asociados a la oxidación de grasas . ◦ Dosis: ▪ Generalmente se usan en una concentración de 2.5 partes por cada 100 partes de sal común . ▪ En la industria cárnica, su uso se limita a cantidades no mayores a 0.2 gramos por cada kilogramo de carne (o 200 mg/kg), consideradas seguras . ▪ La Norma Técnica Colombiana (NTC) 1325 permite un máximo de 200 mg/kg residual como nitrito en productos madurados o fermentados . ▪ A nivel de Colombia, se permite una concentración máxima de 15 mg por cada 100 g de carne . ▪ Un exceso puede conferir un sabor amargo a la carne . • Fosfatos: ◦ Usos: Mejoran la absorción de agua, permiten la emulsificación de la grasa, ayudan a disminuir la pérdida de proteína durante la cocción y reducen el encogimiento de los productos cárnicos . Actúan como modificadores de pH para mantener color y sabor, como alcalinizantes en salmuera, y suavizan las carnes y estabilizan las emulsiones de grasa, agua y proteína . ◦ Dosis: Según la NTC 1325, deben incluirse en 0.5% sobre la masa cárnica, incluyendo la grasa . Una fuente sugiere una dosis para mejorar productos cárnicos de 0.3% a 0.5% . • Almidones (de papa, trigo, yuca, maíz): ◦ Usos: Son comúnmente empleados como espesantes y agentes gelificantes para mejorar la textura, y también como mimetizadores de grasa para simular las propiedades organolépticas y texturales que esta confiere . Cumplen una función estabilizante al incrementar la viscosidad de las emulsiones y ayudan a economizar costos al absorber altas cantidades de agua. El tipo de almidón (e.g., papa vs. trigo) afecta la textura; el almidón de papa puede mejorar la textura de batidos cárnicos cocidos reducidos en grasa al incorporar más agua ligada, lo que contribuye a la elasticidad y estabilidad. El almidón de trigo a altas concentraciones de grasa puede resultar en una textura más dura pero cohesiva . ◦ Consideraciones: Su funcionalidad depende de su origen botánico, tamaño de gránulo, estructura y temperatura de gelificación . El almidón de papa tiene una temperatura de gelificación más baja (60-65°C) que el de trigo (80-85°C). Un exceso de almidones puede afectar la textura, haciéndola más dura . ◦ Dosis: Su uso se encuentra relacionado con las Buenas Prácticas de Manufactura (BPM) . • Sal Común (Cloruro de Sodio): ◦ Usos: Es un conservante que prolonga la vida útil del producto al deshidratar el alimento y evitar el crecimiento microbiano . Actúa como saborizante, en algunos productos puede alterar el color, funciona como vehículo para la penetración de otras sustancias, y es un emulsificante. También aumenta la capacidad de retención de agua (CRA) de la carne . ◦ Dosis: ▪ Los límites de percepción humana de sal son de 1.4% (mínimo) a 2.5% (máximo) . ▪ Se sugiere un rango de 1.6% a 2% para mejorar los productos cárnicos . • Ácidos (Acético, Láctico, Ascórbico, Cítrico): ◦ Usos: Se utilizan como reguladores de acidez, conservantes y antioxidantes para aumentar la estabilidad microbiológica, mantener las carnes en buen estado y evitar la oxidación y el enranciamiento . • Alginatos de Sodio: ◦ Usos: Son polisacáridos extraídos de algas, cuya función principal es ligante, formando un gel que une la mezcla de carne en productos como el jamón . También son humectantes y estabilizadores que previenen la pérdida de jugo de la carne durante su producción y envasado . • Carbonato de Sodio: ◦ Usos: Se emplea como humectante en preparados de carne procesada, especialmente en aves de corral. Ayuda a mantener su consistencia y jugosidad, y a ablandar la carne rápidamente . • Goma Guar: ◦ Usos: Agente de hidratación rápida que ayuda a formar soluciones coloidales viscosas. Se utiliza como espesante, modificador de la viscosidad, aglutinante y lubricante en productos cárnicos como salchichas o carne enlatada . • Dextrosa: ◦ Usos: Monosacárido que aporta energía y actúa como edulcorante bajo en calorías. Se usa para potenciar el sabor o dar un toque dulce a carnes como salchichas y jamón. Además, es un activador de bacterias beneficiosas, mejorando el sabor y aumentando la vida útil en embutidos . • Lecitina de Soya: ◦ Usos: Funciona como emulsionante en productos cárnicos donde puede haber liberación y separación de grasa (ej., embutidos) para evitar dicha separación . • Eritorbato de Sodio: ◦ Dosis: Una fuente sugiere un rango de 0.03% a 0.05% para mejorar los productos cárnicos . • Glutamato Monosódico: ◦ Usos: Es una sal de ácido glutámico utilizada para potenciar los sabores existentes en los productos cárnicos, actuando sobre las papilas gustativas . ◦ Dosis: Su uso está adecuado a las Buenas Prácticas de Manufactura (BPM) . • Aglutinantes y Ablandadores: ◦ Aglutinantes: Se hinchan al añadir agua, siendo muy utilizados para fijar el agua dentro de los productos cárnicos y permitir la cohesión de los ingredientes . Ejemplos incluyen sémola de cebada y trigo, gelatina, harina de soya y huevos . ◦ Ablandadores: Utilizan enzimas extraídas de frutas como la papaya y la piña para una maduración rápida, aumentando la suavidad y el sabor de la carne . ◦ Dosis: No tienen restricciones específicas en la NTC 1325, pero están regulados por las BPM . • Especias y Hierbas: ◦ Usos: De origen vegetal, se añaden para conferir diferentes olores y sabores a los productos . Pueden ser enteras, quebradas o molidas. Los aceites esenciales y oleorresinas son extractos que reemplazan a las especias naturales, ofreciendo estandarización y menor contaminación . ◦ Dosis: No hay cantidades máximas permitidas para especias naturales deshidratadas; su adición depende del consumidor y las BPM . • Proteína Vegetal Hidrolizada (PVH): ◦ Usos: Se obtiene de la hidrólisis ácida de proteínas de soya y maíz, resultando en un sabor similar al cárnico que puede usarse para dar o potenciar el sabor a carne . ◦ Dosis: No tiene restricciones más allá de las BPM . • Humos Naturales Condensados (Humo Líquido): ◦ Usos: Se desarrollan a partir de la condensación del humo producido por la quema de maderas duras no resinosas. Se utilizan para dar sabor ahumado . ◦ Dosis: Se utiliza, por ejemplo, Humo Poly 8.5 en la formulación de chorizo y jamón . Las fuentes también mencionan que las Buenas Prácticas de Manufactura (BPM) son fundamentales en la producción de embutidos cárnicos para asegurar la calidad y la inocuidad del producto final . Las normas técnicas colombianas (NTC) regulan la determinación del contenido de diversos aditivos y parámetros en la carne, como el almidón (NTC 4566), nitratos (NTC 4572), nitritos (NTC 4565), y proteína (NTC 1556)
4	Retenedores	Articulo Web	¡Claro! Cada almidón, fécula o harina tiene un comportamiento único en los embutidos, afectando la textura, retención de agua, gelificación, estabilidad térmica y sinéresis (pérdida de agua). Aquí tienes un análisis detallado de su acción específica en la matriz cárnica: 📌 Fécula de Papa Acción en embutidos: Alta retención de agua (8–10 veces su peso): Ideal para productos que requieren jugosidad (ej. mortadelas, jamones cocidos). Gel suave y elástico: Proporciona una textura delicada y homogénea. Estable en refrigeración: Reduce la sinéresis (pérdida de agua) durante el almacenamiento. Sensible a cizallamiento: No recomendado para procesos de extrusión muy intensos. Dosis recomendada: 2–4% de la masa total. 📌 Fécula de Yuca (Mandioca) Acción en embutidos: Retención media-alta de agua (6–8 veces su peso): Similar a la papa pero con menor viscosidad. Gel más firme y menos pegajoso: Buena para embutidos que necesitan estructura (ej. salchichas tipo Frankfurt). Estable a altas temperaturas: Soporta mejor procesos de cocción prolongados. Neutral en sabor: No enmascara sabores cárnicos. Dosis recomendada: 3–5% de la masa total. 📌 Almidón de Maíz (Maicena) Acción en embutidos: Retención moderada de agua (4–6 veces su peso): Forma geles opacos y menos elásticos. Textura más densa y quebradiza: Usado en productos económicos o donde se busca firmeza (ej. patés). Sinéresis moderada: Puede liberar agua en refrigeración si no se usa con emulsionantes. Requiere cocción completa: Gelatiniza a ~75–80°C. Dosis recomendada: 3–6% de la masa total. 📌 Almidón de Trigo Acción en embutidos: Retención baja-media de agua (3–5 veces su peso): Menor capacidad que féculas de tubérculos. Gel firme y opaco: Aporta cuerpo en productos como morcillas o embutidos de bajo costo. Contiene gluten traza: No apto para productos libres de gluten. Sabor neutro: No interfiere con el perfil de sabores. Dosis recomendada: 4–8% (usado más como relleno económico). 📌 Harina de Trigo Acción en embutidos: Baja retención de agua (1.5–2 veces su peso): Funciona más como extensor económico que como agente de retención. Textura granulosa y densa: Puede endurecer el producto si se usa en exceso. Contiene gluten: Mejora la estructura en productos cocidos, pero no recomendado para embutidos finos. Absorbe jugos: Reduce exudado pero también jugosidad. Dosis recomendada: Máx. 5–10% (solo en productos de bajo costo). 📌 Harina de Arroz Acción en embutidos: Retención baja (2–3 veces su peso): Opción para productos sin gluten. Textura fina y suave: No aporta gomosidad, ideal para embutidos delicados (ej. jamón de pavo). Estable en frío: Menor sinéresis que el almidón de maíz. Sabor neutro y claro: No oscurece el producto. Dosis recomendada: 3–7% de la masa total. 🔍 Comparación Rápida: ¿Cuál Elegir? Criterio Mejor Opción Peor Opción Jugosidad Fécula de papa Harina de trigo Textura suave Fécula de yuca Almidón de maíz Estabilidad térmica Fécula de yuca Harina de trigo Costo bajo Harina de trigo Fécula de papa Sin gluten Harina de arroz Almidón de trigo 💡 Recomendaciones clave: Para embutidos premium (jamón cocido, mortadela): Usa fécula de papa o yuca (alta retención y textura fina). Para salchichas o frankfurts: Almidón de maíz o fécula de yuca (equilibrio entre coste y textura). Productos económicos: Harina de trigo o almidón de trigo (como relleno, pero limita la dosis). Alternativas sin gluten: Harina de arroz + fécula de papa. ¿Tienes una formulación específica donde quieras aplicar estos ingredientes? ¡Puedo ayudarte a optimizar las dosis! 😊
6	relacion agua/ proteina relacion grasa/proteina	Articulo Web	En la elaboración de embutidos, una relación clave para garantizar una buena textura y estabilidad del producto es la relación agua/proteína (A/P). Esta relación indica cuánta agua está siendo retenida por las proteínas en la formulación. Fórmula de la relación Agua/Proteína (A/P): Relacioˊn A/P=%Agua en la foˊrmula%Proteıˊna en la foˊrmula Relacioˊn A/P=%Proteıˊna en la foˊrmula%Agua en la foˊrmula​ Valores recomendados: Embutidos crudos (salchichas frescas, chorizos): Relación A/P ideal: 3.5:1 a 4:1 (es decir, 3.5 a 4 partes de agua por cada parte de proteína). Si supera 4:1, puede haber problemas de exudado (liberación de agua). Si es menor a 3:1, el producto puede quedar seco. Embutidos cocidos (jamones, mortadelas, salchichas tipo Frankfurt): Relación A/P ideal: 3.2:1 a 3.8:1 (dependiendo del tipo de proteína y aditivos usados). Ejemplo de cálculo: Si una fórmula tiene: 60% agua 15% proteína Relacioˊn A/P=6015=4.0 Relacioˊn A/P=1560​=4.0 Este valor está dentro del rango aceptable para embutidos crudos, pero en el límite superior (riesgo de exudado si no hay suficientes proteínas funcionales o aditivos como fosfatos). Factores que afectan la relación A/P: Tipo de proteína: Proteínas con alta capacidad de retención de agua (como las de músculo o aislados de soja) permiten relaciones A/P más altas. Aditivos: Los fosfatos mejoran la retención de agua. Los emulsionantes (como caseinatos) ayudan a estabilizar la mezcla. Procesamiento: Un buen mezclado y emulsificación evita la separación de agua. Ajustes recomendados si la relación es muy alta: Aumentar el % de proteína (añadir proteína de suero, soja o carne magra). Reducir el % de agua (o compensar con hielo durante el mezclado). Usar aditivos retenedores de agua (fosfatos, almidones modificados).
7	Carragenina	Articulo Web	Factor de retención de la carragenina en embutidos\n\n    La carragenina mejora significativamente la capacidad de retención de agua en embutidos, lo cual ayuda a reducir las pérdidas por cocción, mejora la textura (más firme y cohesiva) y el rendimiento del producto. Los niveles más utilizados en formulaciones tipo salchicha suelen ser entre 0.2% y 1.5% sobre el peso del producto, dependiendo de la receta y el objetivo de textura.\n\nCifras específicas del “factor de retención” estándar varían según la formulación, pero el consenso en la literatura es que la adición del 1 a 1.5% de carragenina puede mejorar la retención de agua y el rendimiento en cocción hasta en un 4%-10%, especialmente en embutidos bajos en grasa.\nCantidad de proteína en la carragenina\n\n    La carragenina no es fuente significativa de proteína: contiene solo aproximadamente 0.2g a 0.21g de proteína por cada 100g del aditivo.\n\nEs un polisacárido (carbohidrato) derivado de algas marinas, usado como espesante, gelificante y estabilizante, pero no contribuye contenido proteico relevante a los embutidos.\nResumen en tabla\nParámetro\tDato\nFactor de retención (capacidad de agua)\tMejora entre 4%-10% en retención con 1–1.5% de uso en embutidos\nProteína de la carragenina\t0.2–0.21g por 100g de carragenina\nUso típico en embutidos\t0.2%–1.5% sobre el peso de la mezcla\n\nConclusión:\nLa carragenina aporta principalmente mejoras en la textura y retención de agua en los embutidos, pero su contenido de proteína es prácticamente nulo. Así, su papel es funcional y tecnológico, no nutricional en cuanto a proteínas.
8	Fosfatos 	Articulo Web	Definición y características\n\n    Fosfatos: Son sales y ésteres del ácido fosfórico. En la industria cárnica se utilizan principalmente como aditivos funcionales para modificar la estructura de las proteínas, elevar el pH y mejorar la estabilidad de las emulsiones.\n\n    Principales funciones:\n\n        Mejorar la retención de agua en el producto durante y después de la cocción.\n\n        Favorecer la emulsificación de la grasa y proteínas, mejorando la textura y jugosidad.\n\n        Prevenir la sinéresis (pérdida de agua).\n\n        Secuestrar iones metálicos, lo que ayuda a retrasar la oxidación y el enranciamiento.\n\n        Mejorar el color y prolongar la vida útil.\n\nComposición y tipos de fosfatos usados\n\n    Los más utilizados en embutidos son:\n\n        Tripolifosfato de sodio (STPP, E-451)\n\n        Polifosfato de sodio (E-452)\n\n        Hexametafosfato de sodio (SHMP, E-452i)\n\n        Pirofosfato de sodio (E-450)\n\n    Pueden usarse solos o combinados según el tipo de embutido y sus propiedades deseadas.\n\nDosis recomendadas\n\n    La dosis habitual varía según la legislación de cada país, pero en general no debe superar el 0.5% del peso total del producto (típicamente entre 0.15% y 0.5%).\n\n    Dosis superiores pueden generar texturas indeseadas o afectar el sabor natural del producto y, en exceso, afectar la salud.\n\nModos y etapas de adición\n\n    En seco (mezclados directamente con la carne y demás ingredientes): común en pastas para salchichas, hamburguesas, chorizos y fiambres.\n\n    Solubilizados (en salmuera): empleados para inyección y marinado, seguidos de procesos como masajeado o tumbler, lo que asegura una distribución homogénea de los fosfatos.\n\n    Durante picado-emulsión: en embutidos emulsionados se agregan durante el picado para facilitar la integración homogénea y potenciar su efecto.\n\n    Es importante no sobrepasar el tiempo de mezclado, ya que aportes excesivos pueden dañar la textura.\n\nImportancia de su uso en embutidos\n\n    Mejoran la textura, jugosidad y el rendimiento (menos pérdida por cocción).\n\n    Permiten fabricar productos bajos en sodio al reducir la cantidad necesaria de sal por su efecto sinérgico.\n\n    Prolongan vida útil: evitan oxidación y rancidez.\n\n    Favorecen la unión de piezas en productos reestructurados como nuggets y algunos jamones cocidos.\n\n    Evitan sinéresis en embutidos cocidos y mejoran la estabilidad de las grasas, mejorando la apariencia y aceptación del producto final.\n\nResumen en tabla\nAspecto\tInformación principal\nDefinición\tSales/ésteres del ácido fosfórico, modifican proteínas y estabilizan emulsión\nTipos\tSTPP (E-451), SHMP, polifosfatos (E-452), pirofosfatos (E-450)\nDosis habitual\t0.15%–0.5% del peso total del producto\nModos de adición\tDirecto al mezclado / Soluciones para inyección y masajeado\nEtapas\tPicado, mezcla o emulsión, según el tipo de embutido\nCaracterísticas\tRetención de agua, textura, emulsión, antioxidante, unión de piezas\nImportancia\tMejoran rendimiento, jugosidad, apariencia, vida útil; permiten bajo sodio\n\nConclusión: Los fosfatos son aditivos fundamentales para lograr productos cárnicos emulsionados con textura, rendimiento y jugosidad óptimos, aportando además ventajas tecnológicas y de conservación.
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: formulador_db_user
--

COPY "public"."users" ("id", "username", "password_hash", "full_name", "is_verified", "verification_code", "code_expiry", "session_token") FROM stdin;
13	lyaguana06@gmail.com	scrypt:32768:8:1$OUDfNzNEw6x1RTXA$c97c43c81f6c97ef539812c85f1e331d5f32b150c88396ef838c21261cc7644428642b4606e068e47b8888d8ce1259aa94061668230d3bbb440fa91e472098cb	Leonardo Y	t	\N	\N	b3b833529e97d1c83ebb819b5b3b3d863fe95c072aaa44c94b7583093a51591e
\.


--
-- Data for Name: formulas; Type: TABLE DATA; Schema: public; Owner: formulador_db_user
--

COPY "public"."formulas" ("id", "product_name", "description", "creation_date", "user_id") FROM stdin;
1	Salchicha Tipo Frank prueba 2		2025-08-16T19:35:44.859300	\N
3	Salchicha prueba		2025-08-21T17:33:24.920172	\N
2	salchicha Prueba 1		2025-08-19T03:33:54.680173	\N
10	jamon		2025-09-11T04:13:51.090212	13
\.


--
-- Data for Name: formula_ingredients; Type: TABLE DATA; Schema: public; Owner: formulador_db_user
--

COPY "public"."formula_ingredients" ("id", "formula_id", "ingredient_id", "quantity", "unit") FROM stdin;
2	1	18	5	kg
4	1	16	3	kg
5	1	4	2	kg
7	1	29	2	kg
8	1	15	5	kg
10	1	30	50	g
11	1	26	0.5	kg
12	1	31	73	g
13	1	9	3	g
14	1	11	10	kg
9	1	2	15	kg
3	1	13	5	kg
15	1	32	200	g
6	1	28	0.25	kg
1	1	25	20	kg
18	2	29	5	kg
19	2	2	10	kg
20	2	25	30	kg
21	3	25	50	kg
22	3	18	20	kg
23	3	27	0.35	kg
25	3	30	8	g
26	3	2	20	kg
27	3	29	3	kg
28	3	34	0.1	kg
67	10	52	5	kg
68	10	43	5	kg
69	10	59	25	g
70	10	50	2	g
71	10	56	3	g
72	10	49	1	kg
73	10	65	2	kg
66	10	47	20	kg
74	10	58	1	kg
\.


--
-- Data for Name: user_ingredients; Type: TABLE DATA; Schema: public; Owner: formulador_db_user
--

COPY "public"."user_ingredients" ("id", "name", "protein_percent", "fat_percent", "water_percent", "ve_protein_percent", "notes", "water_retention_factor", "min_usage_percent", "max_usage_percent", "precio_por_kg", "categoria", "user_id") FROM stdin;
43	Agua	\N	\N	100	\N	\N	\N	\N	\N	\N	Agua/Hielo	13
44	Ajo en Polvo	\N	\N	\N	\N	\N	\N	\N	\N	2	Condimento/Aditivo	13
45	Annatto	\N	\N	\N	\N	\N	\N	\N	\N	5	Colorante	13
46	Carmin de Cochinilla	\N	\N	\N	\N	\N	\N	\N	\N	12	Colorante	13
47	Carne de Cerdo	20	5	75	\N	\N	\N	\N	\N	2	Cárnico	13
48	Carne de Pollo	20	3	73	\N	\N	\N	\N	\N	1.5	Cárnico	13
49	Carragenina	\N	\N	\N	\N	\N	10	\N	\N	10	Retenedor/No Cárnico	13
50	Comino	\N	\N	\N	\N	\N	\N	\N	\N	8	Condimento/Aditivo	13
51	Cuero de Cerdo	35	8	57	\N	\N	\N	\N	\N	1.1	Cárnico	13
52	Grasa de Cerdo	11	29	60	\N	\N	\N	\N	\N	0.5	Cárnico	13
53	Harina de Arroz	\N	\N	\N	\N	\N	2	\N	\N	\N	Retenedor/No Cárnico	13
54	Harina de Trigo	\N	\N	\N	\N	\N	1.5	\N	\N	0.3	Retenedor/No Cárnico	13
55	Humo Liquido	\N	\N	\N	\N	\N	\N	\N	\N	10	Condimento/Aditivo	13
56	Nitrito de Sodio	\N	\N	\N	\N	\N	\N	\N	\N	3	Retenedor/No Cárnico	13
57	Pimienta Negra	\N	\N	\N	\N	\N	\N	\N	\N	5	Condimento/Aditivo	13
58	Proteina de Soya	90	0.8	7	\N	\N	\N	\N	\N	5	Retenedor/No Cárnico	13
59	Sal	\N	\N	\N	\N	\N	\N	\N	\N	0.25	Condimento/Aditivo	13
60	Fosfatos	\N	\N	\N	\N	\N	\N	\N	\N	2	Condimento/Aditivo	13
61	Carne de Res 80/20	18	5	72	\N	\N	\N	\N	\N	2.3	Cárnico	13
62	Almidon de Maiz	\N	\N	\N	\N	\N	4	\N	\N	2	Retenedor/No Cárnico	13
63	Almidon de Trigo	\N	\N	\N	\N	\N	3	\N	\N	3	Retenedor/No Cárnico	13
64	CDM	12	24	64	\N	\N	\N	\N	\N	1.1	Cárnico	13
65	Fecula de Papa	\N	\N	\N	\N	\N	8	\N	\N	3	Retenedor/No Cárnico	13
66	Fecula de Yuca	\N	\N	\N	\N	\N	6	\N	\N	2.5	Retenedor/No Cárnico	13
67	fosfato	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	13
68	eritorbato	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	13
69	carne de res	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	13
\.


--
-- Name: bibliografia_id_seq; Type: SEQUENCE SET; Schema: public; Owner: formulador_db_user
--

SELECT pg_catalog.setval('"public"."bibliografia_id_seq"', 8, true);


--
-- Name: formula_ingredients_id_seq; Type: SEQUENCE SET; Schema: public; Owner: formulador_db_user
--

SELECT pg_catalog.setval('"public"."formula_ingredients_id_seq"', 74, true);


--
-- Name: formulas_id_seq; Type: SEQUENCE SET; Schema: public; Owner: formulador_db_user
--

SELECT pg_catalog.setval('"public"."formulas_id_seq"', 10, true);


--
-- Name: ingredients_id_seq; Type: SEQUENCE SET; Schema: public; Owner: formulador_db_user
--

SELECT pg_catalog.setval('"public"."ingredients_id_seq"', 36, true);


--
-- Name: user_ingredients_id_seq; Type: SEQUENCE SET; Schema: public; Owner: formulador_db_user
--

SELECT pg_catalog.setval('"public"."user_ingredients_id_seq"', 69, true);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: formulador_db_user
--

SELECT pg_catalog.setval('"public"."users_id_seq"', 13, true);


--
-- PostgreSQL database dump complete
--

\unrestrict ocR3t8cjzOk8p5ReVGjF54tdpJCcn7ptjhu3fzx8DfgCVUjxXzzsPShvJWNvRnb

