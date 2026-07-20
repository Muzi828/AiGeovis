
// 获取随机数
function getRandomInt(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}
// 国家转换
function covertCountry(content) {
  const data = [];
  content.forEach((obj, index) => {
    // let title = obj.name || obj.contentTitle;
    // 修改这一行，确保使用正确的属性名，并添加默认值防止undefined
    // 打印出当前处理的对象
    // console.log(`处理第${index}个对象:`, JSON.stringify(obj));

    const rawName = (obj.name || obj.contentTitle || "").toString();
    if (!rawName) {
      return; // 跳过无效项
    }
    // 国家层计数：中国台湾 / 香港 / 澳门不单独统计
    const lowerName = rawName.toLowerCase();
    if (
      lowerName.includes("taiwan") ||
      lowerName.includes("hong kong") ||
      lowerName.includes("macau") ||
      lowerName.includes("macao") ||
      lowerName.includes("chinese taipei")
    ) {
      return;
    }
    let title = rawName;
    if (title && typeof title === 'string') {
      // 判断赋值
      if (title.includes("china, mainland")) title = "China";
      if (title.includes("peoples r china")) title = "China";

      if (title.includes("china")) title = "China";
      // if (title.includes("peoples r china")) title = "China";
      if (title.includes("syria")) title = "Syria";
      if (title.includes("japan")) title = "Japan";
      // if (title.includes("usa")) title = "United States";
      if (title.includes("usa")) title = "Usa";
      if (title.includes("france")) title = "France";
      if (title.includes("israel")) title = "Israel";
      if (title.includes("germany")) title = "Germany";
      if (title.includes("australia") || title.includes("austl"))
        title = "Australia";
      if (title.includes("uk")) title = "United Kingdom";
      if (title.includes("canada")) title = "Canada";
      if (title.includes("singapore")) title = "Singapore";
      if (title.includes("pakistan")) title = "Pakistan";
      if (title.includes("denmark")) title = "Denmark";
      if (title.includes("south korea")) title = "Korea";
      if (title.includes("sweden")) title = "Sweden";
      if (title.includes("saudi arabia")) title = "Saudi Arabia";
      if (title.includes("egypt")) title = "Egypt";
      if (title.includes("netherlands")) title = "Netherlands";
      if (title.includes("belgium")) title = "Belgium";
      if (title.includes("india")) title = "India";
      if (title.includes("italy")) title = "Italy";
      if (title.includes("spain")) title = "Spain";
      if (title.includes("switzerland")) title = "Switzerland";
      if (title.includes("malaysia")) title = "Malaysia";
      if (title.includes("romania")) title = "Romania";
      // if (title.includes("taiwan")) title = "China";
      if (title.includes("austria")) title = "Austria";
      if (title.includes("nigeria")) title = "Nigeria";
      if (title.includes("norway")) title = "Norway";
      if (title.includes("poland")) title = "Poland";
      if (title.includes("russia")) title = "Russia";
      if (title.includes("turkey")) title = "Turkey";
      if (title.includes("turkiye")) title = "Turkey";
      if (title.includes("algeria")) title = "Algeria";
      if (title.includes("south africa")) title = "South Africa";
      if (title.includes("finland")) title = "Finland";
      if (title.includes("u arab emirates")) title = "United Arab Emirates";
      if (title.includes("united arab rep")) title = "United Arab Republic";
      if (title.includes("cuba")) title = "Cuba";
      if (title.includes("ghana")) title = "Ghana";
      if (title.includes("greece")) title = "Greece";
      if (title.includes("hungary")) title = "Hungary";
      if (title.includes("morocco")) title = "Morocco";
      if (title.includes("new zealand")) title = "New Zealand";
      if (title.includes("north ireland")) title = "North Ireland";
      if (title.includes("ireland")) title = "Ireland";
      if (title.includes("vietnam")) title = "Vietnam";
      if (title.includes("bangladesh")) title = "Bangladesh";
      if (title.includes("benin")) title = "Benin";
      if (title.includes("brazil")) title = "Brazil";
      if (title.includes("costa rica")) title = "Costa Rica";
      if (title.includes("cyprus")) title = "Cyprus";
      if (title.includes("indonesia")) title = "Indonesia";
      if (title.includes("kenya")) title = "Kenya";
      if (title.includes("sri lanka")) title = "Sri Lanka";
      if (title === "sudan") title = "Sudan";
      if (title === "aland") title = "Aland";
      if (title.includes("south sudan")) title = "South Sudan";
      if (title.includes("ukraine")) title = "Ukraine";
      if (title.includes("uruguay")) title = "Uruguay";
      if (title.includes("bulgaria")) title = "Bulgaria";
      if (title.includes("iran")) title = "Iran";
      if (title.includes("mongolia")) title = "Mongolia";
      if (title.includes("afghanistan")) title = "Afghanistan";
      if (title.includes("angola")) title = "Angola";
      if (title.includes("albania")) title = "Albania";
      if (title.includes("argentina")) title = "Argentina";
      if (title.includes("armenia")) title = "Armenia";
      if (title.includes("azerbaijan")) title = "Azerbaijan";
      if (title.includes("burundi")) title = "Burundi";
      if (title.includes("burkina faso")) title = "Burkina Faso";
      if (title.includes("the bahamas")) title = "The Bahamas";
      if (
          title.includes("bosnia and herzegovina") ||
          title.includes("bosnia & herceg")
      )
        title = "Bosnia and Herzegovina";
      if (title.includes("belarus")) title = "Belarus";
      if (title.includes("belize")) title = "Belize";
      if (title.includes("bermuda")) title = "Bermuda";
      if (title.includes("bolivia")) title = "Bolivia";
      if (title.includes("brunei")) title = "Brunei";
      if (title.includes("bhutan")) title = "Bhutan";
      if (title.includes("botswana")) title = "Botswana";
      if (title.includes("central african republic"))
        title = "Central African Republic";
      if (title.includes("chile")) title = "Chile";
      if (title.includes("ivory coast")) title = "Ivory Coast";
      if (title.includes("cameroon")) title = "Cameroon";
      if (
          title.includes("democratic republic of the congo") ||
          title.includes("dem rep congo")
      )
        title = "Democratic Republic of the Congo";
      if (title.includes("republic of the congo") || title === "rep congo")
        title = "Republic of the Congo";
      if (title.includes("colombia")) title = "Colombia";
      if (title.includes("northern cyprus")) title = "Northern Cyprus";
      if (title.includes("czech republic")) title = "Czech Republic";
      if (title.includes("djibouti")) title = "Djibouti";
      if (title.includes("dominican republic") || title.includes("dominican rep"))
        title = "Dominican Republic";
      if (title.includes("ecuador")) title = "Ecuador";
      if (title.includes("eritrea")) title = "Eritrea";
      if (title.includes("estonia")) title = "Estonia";
      if (title.includes("ethiopia")) title = "Ethiopia";
      if (title.includes("fiji")) title = "Fiji";
      if (title.includes("falkland islands")) title = "Falkland Islands";
      if (title.includes("gabon")) title = "Gabon";
      if (title.includes("georgia")) title = "Georgia";
      if (title === "guinea") title = "Guinea";
      if (title === "bahamas") title = "Bahamas";
      if (title.includes("gambia")) title = "Gambia";
      if (title.includes("guinea bissau")) title = "Guinea Bissau";
      if (title.includes("greenland")) title = "Greenland";
      if (title.includes("guatemala")) title = "Guatemala";
      if (title.includes("french guiana")) title = "French Guiana";
      if (title.includes("guyana")) title = "Guyana";
      if (title.includes("honduras")) title = "Honduras";
      if (title.includes("croatia")) title = "Croatia";
      if (title.includes("haiti")) title = "Haiti";
      if (title.includes("iraq")) title = "Iraq";
      if (title.includes("iceland")) title = "Iceland";
      if (title.includes("jamaica")) title = "Jamaica";
      if (title.includes("jordan")) title = "Jordan";
      if (title.includes("kazakhstan")) title = "Kazakhstan";
      if (title.includes("kyrgyzstan")) title = "Kyrgyzstan";
      if (title.includes("cambodia")) title = "Cambodia";
      if (title.includes("kosovo")) title = "Kosovo";
      if (title.includes("kuwait")) title = "Kuwait";
      if (title.includes("laos")) title = "Laos";
      if (title.includes("lebanon")) title = "Lebanon";
      if (title.includes("liberia")) title = "Liberia";
      if (title.includes("libya")) title = "Libya";
      if (title.includes("sri Lanka")) title = "Sri Lanka";
      if (title.includes("lesotho")) title = "Lesotho";
      if (title.includes("lithuania")) title = "Lithuania";
      if (title.includes("luxembourg")) title = "Luxembourg";
      if (title.includes("latvia")) title = "Latvia";
      if (title.includes("moldova")) title = "Moldova";
      if (title.includes("madagascar")) title = "Madagascar";
      if (title.includes("mexico")) title = "Mexico";
      if (title.includes("macedonia")) title = "Macedonia";
      if (title.includes("mali")) title = "Mali";
      if (title.includes("myanmar")) title = "Myanmar";
      if (title.includes("montenegro")) title = "Montenegro";
      if (title.includes("mozambique")) title = "Mozambique";
      if (title.includes("mauritania")) title = "Mauritania";
      if (title.includes("malawi")) title = "Malawi";
      if (title.includes("namibia")) title = "Namibia";
      if (title.includes("new Caledonia")) title = "New Caledonia";
      if (title === "niger") title = "Niger";
      if (title === "oman") title = "Oman";
      if (title === "tanzania") title = "Tanzania";
      if (title === "congo") title = "Congo";
      if (title === "serbia") title = "Serbia";
      if (title === "dominica") title = "Dominica";
      if (title === "czech rep") title = "Czech Rep";
      if (title === "central african rep") title = "Central African Rep";
      if (title === "bosnia and herz") title = "Bosnia and Herz";
      if (title.includes("nicaragua")) title = "Nicaragua";
      if (title.includes("nepal")) title = "Nepal";
      if (title.includes("panama")) title = "Panama";
      if (title.includes("peru")) title = "Peru";
      if (title.includes("philippines")) title = "Philippines";
      if (title.includes("papua new guinea")) title = "Papua New Guinea";
      if (title.includes("puerto rico")) title = "Puerto Rico";
      if (title.includes("north korea")) title = "North Korea";
      if (title.includes("portugal")) title = "Portugal";
      if (title.includes("paraguay")) title = "Paraguay";
      if (title.includes("qatar")) title = "Qatar";
      if (title.includes("rwanda")) title = "Rwanda";
      if (title.includes("western sahara")) title = "Western Sahara";
      if (title.includes("senegal")) title = "Senegal";
      if (title.includes("solomon islands")) title = "Solomon Islands";
      if (title.includes("sierra leone")) title = "Sierra Leone";
      if (title.includes("el salvador")) title = "El Salvador";
      if (title.includes("somaliland")) title = "Somaliland";
      if (title.includes("somalia")) title = "Somalia";
      if (title.includes("republic of serbia")) title = "Republic of Serbia";
      if (title.includes("suriname")) title = "Suriname";
      if (title.includes("slovakia")) title = "Slovakia";
      if (title.includes("slovenia")) title = "Slovenia";
      if (title.includes("swaziland")) title = "Swaziland";
      if (title.includes("chad")) title = "Chad";
      if (title.includes("togo")) title = "Togo";
      if (title.includes("thailand")) title = "Thailand";
      if (title.includes("tajikistan")) title = "Tajikistan";
      if (title.includes("turkmenistan")) title = "Turkmenistan";
      if (title.includes("east timor")) title = "East Timor";
      if (
          title.includes("trinidad and tobago") ||
          title.includes("trin & tobago") ||
          title.includes("trinidad tobago")
      )
        title = "Trinidad and Tobago";
      if (title.includes("tunisia")) title = "Tunisia";
      if (title.includes("united republic of tanzania"))
        title = "United Republic of Tanzania";
      if (title.includes("uganda")) title = "Uganda";
      if (title.includes("uzbekistan")) title = "Uzbekistan";
      if (title.includes("venezuela")) title = "Venezuela";
      if (title.includes("vanuatu")) title = "Vanuatu";
      if (title.includes("west bank")) title = "West Bank";
      if (title.includes("yemen")) title = "Yemen";
      if (title.includes("zambia")) title = "Zambia";
      if (title.includes("zimbabwe")) title = "Zimbabwe";
      if (title.includes("w. Sahara")) title = "W. Sahara";
      if (title.includes("lao pdr")) title = "Lao PDR";
      if (title.includes("dem.rep.korea")) title = "Dem.Rep.Korea";
      if (title.includes("falkland is")) title = "Falkland Is";
      if (title.includes("timor-leste")) title = "Timor-Leste";
      if (title.includes("solomon is")) title = "Solomon Is";
      if (title.includes("palestine")) title = "Palestine";
      if (title.includes("n. cyprus")) title = "N. Cyprus";
      if (title.includes("fr. s. antarctic lands"))
        title = "Fr. S. Antarctic Lands";
      if (title.includes("mauritius")) title = "Mauritius";
      if (title.includes("comoros")) title = "Comoros";
      if (title.includes("eq. guinea")) title = "Eq. Guinea";
      if (title.includes("guinea-bissau")) title = "Guinea-Bissau";
      if (title.includes("saint lucia") || title.includes("st lucia"))
        title = "Saint Lucia";
      if (title.includes("antigua and barb")) title = "Antigua and Barb";
      if (title.includes("u.s. virgin is")) title = "U.S. Virgin Is";
      if (title.includes("montserrat")) title = "Montserrat";
      if (title.includes("grenada")) title = "Grenada";
      if (title.includes("barbados")) title = "Barbados";
      if (title.includes("samoa")) title = "Samoa";
      if (title.includes("cayman is")) title = "Cayman Is";
      if (title.includes("faeroe is")) title = "Faeroe Is";
      if (title.includes("isie of man")) title = "IsIe of Man";
      if (title.includes("malta")) title = "Malta";
      if (title.includes("jersey")) title = "Jersey";
      if (title.includes("cape verde")) title = "Cape Verde";
      if (title.includes("turks and caicos is")) title = "Turks and Caicos Is";
      if (title.includes("st. vin. and gren")) title = "St. Vin. and Gren";
      if (title.includes("liechtenstein")) title = "Liechtenstein";
      if (title.includes("yugoslavia")) title = "Yugoslavia";
      if (title.includes("bahrain")) title = "Bahrain";
      if (title.includes("andorra")) title = "Andorra";
      if (title.includes("cote ivoire")) title = "Cote d'Ivoire";
      if (title.includes("faroe islands")) title = "Faroe Islands";
      if (title.includes("holland")) title = "Holland";
      if (title.includes("monaco")) title = "Monaco";
      if (title.includes("unknow")) title = "Unknow";
      if (title.includes("england")) title = "England";
      if (title.includes("wales")) title = "Wales";
      if (title.includes("scotland")) title = "Scotland";
      if (title.includes("turkiye")) title = "Turkiye";
    }

    // 添加数据
    // data.push({ value: obj.value, name: title });
    // 添加数据
    data.push({ value: obj.value, name: title });
  });
  // console.log(data)
  return data;
}



export {
  covertCountry,
  getRandomInt,
};
