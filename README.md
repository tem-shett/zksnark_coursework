# zkSNARK Coursework

Добро пожаловать в репозиторий zkSNARK Coursework!
Здесь собраны утилиты для работы с R1CS–файлами: их оптимизации, проверки через Nova и проведения операций с ансамблями схем.

---

## Содержание

- [1. Формат R1CS JSON-файлов](#1-формат-r1cs-json-файлов)  
- [2. Оптимизация R1CS](#2-оптимизация-r1cs)  
- [3. Проверка R1CS через Nova](#3-проверка-r1cs-через-nova)  
- [4. Ансамбли R1CS](#4-ансамбли-r1cs)  
  - [4.1. Запись файлов ансамбля](#41-запись-файлов-ансамбля)  
  - [4.2. Объединение ансамбля в единый R1CS](#42-объединение-ансамбля-в-единый-r1cs)  

---

## 1. Формат R1CS JSON-файлов

Все R1CS JSON-файлы в этом проекте должны иметь следующий формат:

```json
{
  "num_variables": 4,
  "num_public_inputs": 1,
  "num_constraints": 1,
  "io_size": 1,
  "scheme_length": 2,
  "constraints": [
    {
      "A": [
        { "variable": 0, "coefficient": "1" },
        { "variable": 1, "coefficient": "1" }
      ],
      "B": [
        { "variable": 2, "coefficient": "1" }
      ],
      "C": [
        { "variable": 3, "coefficient": "1" }
      ]
    }
  ],
  "public_inputs": ["1", "1"],
  "witness": ["4", "4", "2", "10"]
}
```
Где

`num_variables` — общее число переменных.

`num_public_inputs` — число публичных входов.

`num_constraints` — количество ограничений.

`io_size` — число переменных сквозного входа-выхода между итерациями.

`scheme_length` — число итераций в доказательстве.

`constraints` — список ограничений в формате $A \cdot B = C$.

`public_inputs` — массив строковых значений публичных входов.

`witness` — массив строковых значений свидетелей.

## 2. Оптимизация R1CS

Для оптимизации существующего файла R1CS запустите:

```bash
python optimizations/optimize_r1cs.py <source_file> <target_file>
```

`<source_file>` — путь к исходному JSON-файлу.

`<target_file>` — путь, куда будет записан оптимизированный результат.

## 3. Проверка R1CS через Nova

Чтобы проверить корректность R1CS-файла с помощью движка Nova:

```bash
# 1) Соберите проект:
cargo build

# 2) Запустите проверку:
target/debug/zksnark_coursework <source_file>
```

Заранее убедитесь, что Nova (https://github.com/microsoft/Nova/tree/main) установлена.

## 4. Ансамбли R1CS

### 4.1. Запись файлов ансамбля

Ансамблем (ensemble) считается упорядоченный список (JSON-массив) из нескольких R1CS JSON-объектов:

```json
[
  { /* R1CS #0 */ },
  { /* R1CS #1 */ },
  { /* R1CS #2 */ }
]
```

Если внутри одного R1CS требуется ссылка на переменную другого, используйте массив `[индекс_R1CS_в_массив, номер_переменной]`:

```json
"A": [
  { "variable": [1, 3], "coefficient": "5" }
]
```

### 4.2. Объединение ансамбля в единый R1CS

Чтобы склеить ансамбль из нескольких R1CS в один R1CS, выполняющий тот же функционал, запустите:

```bash
python optimizations/ensemble_to_r1cs.py <source_ensemble.json> <target.json>
```

`<source_ensemble.json>` — JSON-массив R1CS-объектов.
`<target.json>` — выходной объединённый R1CS-файл.
