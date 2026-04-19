# Tabela empresa_junior
| Name           | Format                   | Type    | Description |
|----------------|--------------------------|---------|-------------|
| id             | bigint                   | number  |             |
| id_ej          | bigint                   | number  |             |
| nome           | text                     | string  |             |
| cnpj           | text                     | string  |             |
| ano_federacao  | integer                  | number  |             |
| federacao      | text                     | string  |             |
| cluster        | integer                  | number  |             |
| comunidade     | text                     | string  |             |
| estado         | text                     | string  |             |
| cidade         | text                     | string  |             |
| universidade   | text                     | string  |             |
| curso          | text                     | string  |             |
| status         | text                     | string  |             |
| created_at     | timestamp without time zone | string |             |
| updated_at     | timestamp without time zone | string |             |
| foto_url       | text                     | string  |             |

# Tabela metas
| Name                   | Format  | Type    | Description |
|------------------------|---------|---------|-------------|
| id                     | bigint  | number  |             |
| id_ej                  | bigint  | number  |             |
| ano                    | integer | number  |             |
| meta_faturamento       | numeric | number  |             |
| meta_taxa_colaboracao  | numeric | number  |             |
| meta_csat              | numeric | number  |             |
| meta_projetos_impacto  | integer | number  |             |
| meta_pdi               | boolean | boolean |             |
| meta_engajamento_mej   | numeric | number  |             |
| created_at             | timestamp without time zone | string |             |

# Tabela monitoramento
| Name                        | Format  | Type    | Description |
|-----------------------------|---------|---------|-------------|
| id                          | bigint  | number  |             |
| id_ej                       | bigint  | number  |             |
| ano                         | integer | number  |             |
| mes                         | integer | number  |             |
| faturamento_mes             | numeric | number  |             |
| faturamento_acumulado       | numeric | number  |             |
| faturamento_colab_mes       | numeric | number  |             |
| faturamento_colab_acumulado | numeric | number  |             |
| projetos_vendidos_mes       | integer | number  |             |
| projetos_totais             | integer | number  |             |
| csat                        | numeric | number  |             |
| numero_membros              | integer | number  | Total de membros da EJ |
| membros_engajados_mes       | integer | number  | Membros que participaram de evento MEJ no mês (0 se nenhum) |
| created_at                  | timestamp without time zone | string |             |
