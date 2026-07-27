# Nenormal
Добавь во вкладку OPTIMIZATION приложения NOA RUST TOOL следующие функции. Каждая функция должна иметь:

Переключатель ON/OFF Статус текущего состояния и Кнопку ОТКАТ которая бцдет возвращать все как было

Также добавь кнопку «Создать точку восстановления», которая открывает: textrundll32.exe shell32.dll,Control_RunDLL sysdm.cpl,,4 

Список функций:

Enable Windows Game Mode
 Включает игровой режим Windows Путь: Параметры → Игры → Игровой режим → Вкл При отключении вернуть стандартное состояние

Enable High Performance Power Plan
Переключает план питания Windows на «Высокая производительность»

Enable Ultimate Performance Power Plan
Создаёт и включает режим «Максимальная производительность» Команда: powercfg -duplicatescheme e9a42b02-d5df-448d-aa00-03f14749eb61 При отключении — вернуть предыдущий план питания

Disable Xbox Game Bar
Отключает Xbox Game Bar Параметры → Игры → Xbox Game Bar

Disable Background Recording
Отключает запись в фоне Параметры → Игры → Захваты
