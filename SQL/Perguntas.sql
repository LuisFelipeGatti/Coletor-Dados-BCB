-- =====================================================================
-- Perguntas de negócio respondidas com SQL (banco: dados/bcb.db)
-- Cada consulta tem um título (linha de PERGUNTA) e termina com ";"
-- =====================================================================


-- PERGUNTA 1: Quantos registros e qual o período coberto por cada série?
SELECT
    s.nome                AS serie,
    COUNT(*)              AS registros,
    MIN(o.data)           AS primeira_data,
    MAX(o.data)           AS ultima_data
FROM observacoes AS o
JOIN series AS s ON s.codigo = o.codigo_serie
GROUP BY s.nome
ORDER BY s.nome;


-- PERGUNTA 2: Qual foi a cotação média, mínima e máxima do dólar em cada ano?
SELECT
    strftime('%Y', data)  AS ano,
    ROUND(AVG(valor), 4)  AS media,
    ROUND(MIN(valor), 4)  AS minima,
    ROUND(MAX(valor), 4)  AS maxima
FROM observacoes
WHERE codigo_serie = 1
GROUP BY ano
ORDER BY ano;


-- PERGUNTA 3: Em que dias o dólar atingiu sua maior e sua menor cotação no período?
SELECT 'maior cotação' AS extremo, data, valor
FROM observacoes
WHERE codigo_serie = 1
  AND valor = (SELECT MAX(valor) FROM observacoes WHERE codigo_serie = 1)

UNION ALL

SELECT 'menor cotação', data, valor
FROM observacoes
WHERE codigo_serie = 1
  AND valor = (SELECT MIN(valor) FROM observacoes WHERE codigo_serie = 1);


-- PERGUNTA 4: Quanto o dólar variou (%) em cada ano, do primeiro ao último dia útil?
WITH limites AS (
    SELECT
        strftime('%Y', data) AS ano,
        MIN(data)            AS primeiro_dia,
        MAX(data)            AS ultimo_dia
    FROM observacoes
    WHERE codigo_serie = 1
    GROUP BY ano
)
SELECT
    l.ano,
    ini.valor                                          AS cotacao_inicial,
    fim.valor                                          AS cotacao_final,
    ROUND((fim.valor / ini.valor - 1) * 100, 2)        AS variacao_pct
FROM limites AS l
JOIN observacoes AS ini ON ini.codigo_serie = 1 AND ini.data = l.primeiro_dia
JOIN observacoes AS fim ON fim.codigo_serie = 1 AND fim.data = l.ultimo_dia
ORDER BY l.ano;


-- PERGUNTA 5: Quais foram os 5 meses com a maior inflação (IPCA)?
SELECT
    strftime('%m/%Y', data) AS mes,
    valor                   AS ipca_pct
FROM observacoes
WHERE codigo_serie = 433
ORDER BY valor DESC
LIMIT 5;


-- PERGUNTA 6: Em quantos meses de cada ano houve deflação (IPCA negativo)?
SELECT
    strftime('%Y', data)                          AS ano,
    SUM(CASE WHEN valor < 0 THEN 1 ELSE 0 END)    AS meses_com_deflacao,
    COUNT(*)                                      AS meses_no_ano
FROM observacoes
WHERE codigo_serie = 433
GROUP BY ano
ORDER BY ano;


-- PERGUNTA 7: Em quais datas a meta Selic mudou, e de quanto foi cada mudança?
WITH selic AS (
    SELECT
        data,
        valor,
        LAG(valor) OVER (ORDER BY data) AS valor_anterior
    FROM observacoes
    WHERE codigo_serie = 432
)
SELECT
    data                              AS data_mudanca,
    valor_anterior                    AS de,
    valor                             AS para,
    ROUND(valor - valor_anterior, 2)  AS variacao_pp,
    CASE WHEN valor > valor_anterior THEN 'alta' ELSE 'corte' END AS tipo
FROM selic
WHERE valor <> valor_anterior
ORDER BY data;


-- PERGUNTA 8: Lado a lado: dólar médio, Selic média e meses de deflação por ano.
WITH dolar AS (
    SELECT strftime('%Y', data) AS ano, AVG(valor) AS dolar_medio
    FROM observacoes WHERE codigo_serie = 1 GROUP BY ano
),
selic AS (
    SELECT strftime('%Y', data) AS ano, AVG(valor) AS selic_media
    FROM observacoes WHERE codigo_serie = 432 GROUP BY ano
),
ipca AS (
    SELECT strftime('%Y', data) AS ano,
           SUM(CASE WHEN valor < 0 THEN 1 ELSE 0 END) AS meses_deflacao
    FROM observacoes WHERE codigo_serie = 433 GROUP BY ano
)
SELECT
    d.ano,
    ROUND(d.dolar_medio, 4)  AS dolar_medio,
    ROUND(s.selic_media, 2)  AS selic_media_pct,
    i.meses_deflacao
FROM dolar AS d
JOIN selic AS s ON s.ano = d.ano
LEFT JOIN ipca AS i ON i.ano = d.ano
ORDER BY d.ano;

