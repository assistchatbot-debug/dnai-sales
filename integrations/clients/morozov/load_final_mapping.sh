#!/bin/bash
echo "📦 Загрузка последних 15 товаров..."

declare -a mappings=(
"241|Royal Tools маникюрная пилка для кутикулы RTVP|RT-CUTICLE-FILE|Пилочка для кутикулы Royal Tools"
"249|Royal Tools маникюрные ножницы RT45837|RT45837|Ножницы кутикульные RT 45837"
"255|Royal Tools кусачки-книпсер RT30818|RT30818|Книпсер маникюрный RT30818"
"257|Royal Tools пинцет|RT-TWEEZERS|Пинцет наклонный gold RT 11401"
"265|Royal Tools терка педикюрная RTS 80-120|RT-GRATER-SILICONE|Тёрка для ног лазерная с силиконовой вставкой RT"
"273|BAROCCO массажная расческа Aurum|BAROCCO-AURUM|Расческа Barocco Royal Purpur фиолетовый"
"275|BAROCCO массажная расческа Le Brilliant|BAROCCO-BRILLIANT|Расческа Barocco Le Brilliant"
"277|Маска для подтяжки овала лица 24К|FACE-MASK-24K|Маска для подтяжки овала лица"
"287|НЕ ВЫБИРАЙТЕ Гранат 20гр х 15шт|POMEGRANATE-SKIP|Гранат-коллагеновое желе (20 гр х 15 шт)"
"291|Коллаген морской корейский желе 280|MARINE-COLLAGEN|Бальзам Rose Balm RT, 15 г"
"301|Dr.Water Biocera щелочные керамические шарики|BIOCERA-BALLS|Щелочной треугольник"
"303|Esteau портативный увлажнитель для лица|ESTEAU-PORT|Водородный спрей ESTEAU"
"305|Мисс Кругляшка Жемчужина Cozcore|MISS-PEARL|Мисс Кругляшка Жемчужина Cozcore"
"315|Конверт для штучек бумажный бордовый RT|RT-ENVELOPE|Футляр для маникюрных принадлежностей"
)

for mapping in "${mappings[@]}"; do
    IFS='|' read -r id name code name_1c <<< "$mapping"
    
    echo "➕ ID $id → $code"
    
    curl -s -X POST https://bizdnai.com/morozov/api/mapping/product \
      -H "Content-Type: application/json" \
      -d "{
        \"bitrix24_product_id\": \"$id\",
        \"bitrix24_product_name\": \"$name\",
        \"onec_product_code\": \"$code\",
        \"onec_product_name\": \"$name_1c\"
      }" > /dev/null && echo "   ✅" || echo "   ❌"
    
    sleep 0.1
done

echo ""
echo "✅ Загружено!"
echo ""
curl -s https://bizdnai.com/morozov/api/mapping/products | python3 -c "import json,sys; m=json.load(sys.stdin)['mappings']; print(f'🎉 ИТОГО: {len(m)}/80 активных товаров = {len(m)/80*100:.0f}%')"

