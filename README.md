# Nenormal
Добавь во вкладку OPTIMIZATION приложения NOA RUST TOOL следующие функции. Каждая функция должна иметь:

Checkbox ON/OFF
Статус текущего состояния
Кнопку ПРИМЕНИТЬ
Кнопку ОТКАТ

Также добавь кнопку «Создать точку восстановления», которая открывает:
textrundll32.exe shell32.dll,Control_RunDLL sysdm.cpl,,4
Список функций:
1. Enable Windows Game Mode

Включает игровой режим Windows
Путь: Параметры → Игры → Игровой режим → Вкл
При отключении вернуть стандартное состояние

2. Enable High Performance Power Plan

Переключает план питания Windows на «Высокая производительность»

3. Enable Ultimate Performance Power Plan

Создаёт и включает режим «Максимальная производительность»
Команда: powercfg -duplicatescheme e9a42b02-d5df-448d-aa00-03f14749eb61
При отключении — вернуть предыдущий план питания

4. Disable Xbox Game Bar

Отключает Xbox Game Bar
Параметры → Игры → Xbox Game Bar

5. Disable Background Recording

Отключает запись в фоне
Параметры → Игры → Захваты
