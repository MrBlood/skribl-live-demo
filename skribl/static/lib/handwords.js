/* YOUR HAND WRITES THE WORDS on an empty canvas (the owner's pick after the
 * "Empty canvas ideas" mock, filmed together: "Go, all yes"). "Draw anything"
 * on the Pad and "Draw page 1" on Flip write themselves in the owner's own
 * hand, in about two seconds, every time the words appear: an empty canvas on
 * open, Undo back to nothing, a new Skribl. The first stroke un-writes them.
 *
 * A RECORDING, NOT A FONT. harness/tools/make_handwords.py writes the words
 * with the real Text tool in Skribl's style (the owner's letters) on the real
 * Pad and keeps what the Pad recorded, between MARK:BEGIN and MARK:END below:
 * each stroke as [x, y, ms, x, y, ms, ...] in the words' own box, timed to
 * the owner's "about 2 seconds, as filmed". Words with no recording keep
 * their typed letters.
 *
 * ONE PATH IN currentColor: the words' own grey, so a theme, a canvas colour
 * and its contrast follow without this module, and a single path never lays
 * its grey twice where strokes cross. The typed words stay in the page, out of
 * sight, for a screen reader; the drawing is aria-hidden.
 *
 * WHEN: it watches the class the editors already set on the words (hidden
 * once there is ink), so app.js, which the link player loads, gains nothing.
 * Under the first-open hello it waits, blank, and writes once the hello has
 * gone. Reduce Motion: the words are there whole, at once. The editors' head
 * (_skribl_hand_boot.html) keeps the typed letters unseen until this takes
 * over, and fades them in on their own at 1.2 s in case it never does.
 *
 * IT LOADS ON ITS OWN (async, just after the words and the hello in both
 * editors), not behind their hundred-odd deferred scripts: on a slow first
 * open those took 5 to 9 s, the typed words showed at 1.2 s, and then the
 * hand took them away to write them (the owner: "it shows the old draw
 * anything while it loads"). It needs nothing they make. Where the typed
 * words have shown all the same, they stay: no swap. The snail waits for
 * those scripts, because the canvas can move as they lay it out.
 *
 * THE SNAIL, ONCE, IN A SITE'S POST BOX, where the hello never plays: after
 * the words, How it works' snail draws itself faintly above them and rests;
 * on Flip a ball bounces three times and on the fourth landing splats into
 * drops that fly out and are gone, and then its box fades (data-end "go";
 * with Reduce Motion it does not come). The first stroke sweeps either away. Once per
 * device in each editor, as the hello is once (?once=again plays it again):
 * a post box opens on the Pad and Flip is its ⋯ row away, so one mark for
 * both spent the snail's once and the ball never came. The templates add
 * it in compose mode only (_skribl_hint_once.html), and automation never
 * meets it unless it asks (window.__skriblOnceForce), as with the hello.
 * Played by the in-post player, fetched only then.
 *
 * Exports nothing: verify_identity drives it through the words' class and
 * reads the drawing's own data-state.
 */
(function () {
  'use strict';
  var hint = document.getElementById('canvasEmptyHint') || document.getElementById('flipEmptyHint');
  var title = hint && hint.firstElementChild;
  if (!title) return;

  // MARK:BEGIN harness/tools/make_handwords.py writes the next line
  var WORDS = {"Draw anything":{"box":[530.0,91.4],"size":9,"ms":1900,"strokes":[[10.9,8.4,0,10.5,11.4,8,10.5,14.4,10,10.5,17.6,13,10.5,20.9,16,10.5,23.5,16,10.5,26.0,19,10.5,28.6,19,10.5,31.4,22,10.5,33.9,22,10.5,36.5,24,10.5,39.1,24,10.7,41.6,27,10.7,44.2,27,10.9,46.5,30,10.9,49.1,30,11.3,51.4,33,11.6,54.6,36,11.9,58.4,39,12.1,61.4,42,12.1,62.8,45],[9.3,9.1,53,11.9,7.7,63,14.9,7.7,66,17.7,7.7,69,20.9,7.9,72,24.4,8.4,75,28.1,8.8,78,32.1,9.5,80,36.0,10.9,83,38.9,12.3,86,41.9,13.9,89,44.4,15.7,91,47.0,17.7,92,49.4,19.5,95,51.6,21.4,98,54.2,24.4,100,56.0,27.4,103,57.0,30.9,106,57.2,34.6,109,57.0,38.6,112,55.8,41.8,115,54.6,43.9,115,53.0,46.0,118,51.4,48.4,118,49.5,50.7,121,47.4,52.8,121,45.1,54.6,123,42.8,56.5,123,40.2,57.9,126,37.7,59.1,126,35.3,60.2,129,33.0,61.1,129,30.5,61.6,132,27.9,62.1,132,24.6,62.1,135,22.3,62.1,135,19.2,62.1,137,16.3,62.1,140,12.8,61.6,143,10.0,60.7,146,7.0,59.8,149,6.5,59.5,149],[67.7,22.3,158,68.1,25.1,165,68.1,27.9,168,68.4,31.4,171,68.4,34.5,172,68.4,37.8,175,68.4,41.1,176,68.4,44.3,179,68.4,47.4,182,67.9,51.4,185,67.7,55.1,188,67.7,58.4,191,67.7,61.1,193,67.7,58.1,211,67.9,54.9,213,68.1,51.4,216,68.2,48.7,218,68.6,45.8,219,69.3,42.7,222,70.0,39.5,225,70.7,37.2,225,72.1,33.5,228,73.9,30.2,230,76.3,27.9,233,78.8,26.3,236,81.6,25.3,239,84.2,24.9,242,87.4,25.3,248,89.1,27.4,250,90.0,30.4,253],[102.3,34.4,262,103.2,32.1,291,104.9,30.2,294,107.0,28.8,299,109.3,27.7,302,111.6,26.7,308,114.2,26.3,311,117.2,26.0,316,120.0,26.0,322,122.3,27.0,331,123.7,28.8,336,124.9,31.4,345,125.6,33.9,351,125.8,36.5,356,125.8,39.1,359,125.8,41.8,365,125.8,44.4,371,125.8,47.0,376,126.0,49.5,382,126.0,52.1,388,126.5,54.6,393,126.5,57.2,402,126.7,60.0,413,126.7,57.4,439,127.0,54.6,442,127.0,52.1,448,127.0,49.3,453,126.0,46.7,459,125.1,44.4,465,122.8,43.2,470,120.0,43.2,476,117.0,43.2,482,114.2,43.7,485,111.4,44.6,490,108.4,46.0,493,105.6,47.9,499,103.2,49.5,502,101.6,51.4,508,100.7,53.7,516,100.5,56.3,522,100.7,59.1,530,102.1,61.1,539,104.6,62.1,545,107.4,62.3,550,110.7,62.1,553,113.9,61.1,559,116.5,60.2,562,119.1,59.1,565,121.4,57.9,568,123.7,57.0,570,126.5,55.8,573,128.8,54.9,579,130.2,54.2,582],[140.7,28.8,590,141.4,31.4,595,141.6,34.2,597,142.8,37.7,600,144.2,40.9,603,145.3,43.5,604,146.7,45.8,605,148.4,49.3,608,150.2,52.8,611,151.6,56.0,614,152.8,58.6,617,154.4,60.9,625,155.3,57.9,634,156.3,54.6,637,157.2,50.9,640,158.4,47.7,641,159.2,45.4,643,160.4,42.3,645,161.2,40.1,647,162.1,38.0,648,163.5,35.1,651,164.9,31.8,654,166.3,29.5,657,166.7,32.3,668,166.5,34.6,671,166.3,37.4,674,166.3,40.4,677,166.3,43.7,680,166.7,47.2,682,167.9,50.2,685,169.1,53.0,688,170.4,55.1,691,172.3,57.2,694,174.4,58.8,700,176.7,58.6,711,177.7,55.8,717,178.4,52.6,720,179.4,49.6,721,180.1,47.4,722,180.8,45.2,724,181.6,42.8,725,182.6,40.4,725,183.5,37.9,728,184.4,35.6,728,185.3,33.0,731,186.5,30.7,731,187.4,28.6,734,188.7,26.5,735,190.2,23.7,737,191.4,21.8,740],[229.3,32.3,748,230.7,30.3,756,232.3,28.6,758,235.1,27.0,761,237.9,25.8,764,240.2,24.9,767,242.8,23.9,770,245.3,23.2,773,247.9,22.8,776,251.2,22.8,778,253.9,23.2,784,255.6,25.1,787,256.7,27.2,790,257.4,29.8,792,258.1,32.3,795,258.1,35.3,798,258.1,38.4,801,258.1,41.8,804,257.9,45.3,807,257.2,48.6,810,257.0,51.4,813,256.7,54.2,815,256.5,57.4,821,256.3,60.0,824,255.1,57.4,844,254.9,54.4,847,254.6,51.6,850,254.4,49.1,852,253.9,46.3,855,253.2,43.7,858,252.6,41.1,861,250.7,38.4,867,247.9,37.0,870,245.1,37.0,872,242.1,37.7,875,238.8,39.3,878,235.8,40.9,881,232.6,42.6,884,229.8,44.4,887,227.2,46.3,890,224.9,48.8,892,223.5,51.1,895,222.8,53.7,901,223.7,56.0,904,226.5,56.7,910,229.3,57.0,912,232.6,57.0,915,236.3,56.7,918,239.2,56.3,920,241.4,55.8,921,244.6,54.9,924,247.2,54.2,924,249.8,53.2,927,252.1,52.6,927,254.9,51.6,930,257.4,50.7,930,258.6,50.2,930],[269.1,23.5,938,269.1,26.3,951,269.1,29.8,954,269.1,33.0,957,269.1,36.7,960,269.1,40.2,962,269.1,43.9,965,269.1,47.4,968,269.1,50.9,971,269.1,54.2,974,269.1,57.2,977,269.1,60.2,980,269.3,62.6,985,269.5,60.0,1000,269.8,57.4,1003,270.0,54.2,1005,270.7,50.4,1008,271.4,47.2,1010,272.0,45.0,1011,272.6,42.8,1011,273.5,40.2,1014,274.2,37.9,1014,275.1,35.3,1017,276.0,33.0,1017,277.2,30.7,1020,278.4,28.6,1020,279.8,26.7,1022,282.6,23.7,1025,285.6,22.3,1028,288.1,21.8,1031,290.5,22.1,1034,292.6,23.7,1037,293.9,26.3,1040,295.1,29.3,1042,295.3,32.8,1045,295.6,36.0,1048,295.6,39.3,1051,295.6,42.8,1054,295.6,46.3,1057,295.3,49.8,1060,295.1,53.2,1062,294.9,56.7,1065,294.9,59.5,1068,294.9,62.1,1071,294.9,62.6,1071],[311.6,26.0,1080,311.2,29.1,1087,311.6,31.4,1090,312.6,33.7,1093,313.9,36.5,1096,315.3,38.8,1098,317.0,41.4,1101,318.5,44.2,1103,320.2,47.0,1104,321.6,48.8,1107,323.4,51.6,1108,325.1,54.2,1110,327.2,57.0,1112,329.5,59.1,1115,333.5,60.0,1121,336.0,60.0,1124,337.2,60.0,1127],[345.6,26.5,1135,343.7,28.8,1138,342.6,32.1,1140,341.5,35.0,1143,340.7,38.1,1146,339.6,41.3,1147,338.8,44.4,1148,338.0,47.4,1151,337.4,49.8,1151,336.5,53.0,1154,335.6,56.3,1157,334.9,58.6,1157,333.9,61.1,1160,333.0,63.7,1160,331.9,66.3,1163,330.5,69.1,1163,329.3,71.6,1166,327.7,73.9,1166,326.0,76.3,1168,324.4,78.4,1168,322.6,80.2,1171,320.5,81.6,1171,318.4,83.0,1174,316.3,83.9,1174,312.6,84.9,1177,308.8,84.4,1180,306.0,82.1,1183],[369.3,17.0,1191,369.3,20.0,1196,369.3,23.0,1198,369.3,26.5,1201,369.2,29.4,1203,369.1,32.8,1206,368.8,35.1,1207,368.6,37.7,1207,368.4,40.2,1210,368.1,42.8,1210,368.1,45.1,1213,367.9,47.4,1213,367.7,49.8,1216,367.4,53.0,1218,367.4,57.0,1221,367.4,60.2,1224,368.1,62.8,1227,370.5,63.7,1233,373.0,63.2,1236,374.9,61.3,1238,377.0,58.8,1241,378.4,56.7,1241,379.8,54.6,1244,380.5,53.7,1244],[356.0,25.3,1253,358.6,24.4,1260,361.9,24.4,1263,364.8,24.4,1264,367.9,24.4,1266,371.0,24.4,1269,374.4,24.4,1272,377.0,24.4,1272,380.5,24.6,1274,382.5,24.6,1277],[398.6,6.5,1286,398.4,9.5,1301,398.1,12.6,1304,398.1,15.8,1307,397.8,18.9,1310,397.7,21.3,1311,397.5,23.7,1313,397.2,26.3,1313,397.0,28.6,1316,396.9,30.9,1317,396.5,33.2,1319,396.3,35.6,1319,395.8,38.8,1321,395.5,42.0,1324,395.1,45.1,1327,394.9,48.8,1330,394.4,52.3,1333,393.9,55.6,1336,393.5,58.4,1338,393.2,61.1,1341,393.0,58.4,1356,393.7,55.8,1358,394.4,53.0,1361,395.3,49.8,1364,396.5,46.0,1367,397.4,42.6,1370,398.4,38.6,1373,399.5,34.9,1376,400.7,31.4,1379,402.1,28.6,1381,403.7,26.3,1384,406.3,24.6,1390,409.5,24.2,1393,412.8,24.2,1398,415.3,25.6,1401,417.2,27.0,1404,419.3,28.6,1407,421.1,30.2,1410,422.8,32.1,1413,424.2,34.2,1416,425.3,36.7,1418,426.5,39.1,1421,426.7,42.3,1424,427.0,45.8,1427,426.9,48.7,1429,426.0,51.6,1430,425.1,54.6,1433,424.2,56.7,1436,423.2,58.8,1436,422.1,62.3,1438,421.6,65.3,1441,421.6,68.4,1447,421.9,68.6,1447],[438.8,27.4,1456,438.4,30.2,1469,438.4,33.7,1472,438.4,37.0,1475,438.4,39.3,1475,438.4,41.8,1477,438.4,44.2,1477,438.1,46.5,1480,437.9,49.8,1480,437.7,52.9,1483,437.4,55.8,1486,437.4,58.8,1489,437.4,62.1,1492,437.9,64.9,1497,438.4,66.3,1500],[438.8,13.7,1509,438.8,13.7,1509],[451.9,23.0,1517,450.0,25.6,1527,450.0,28.4,1530,450.0,31.1,1533,450.0,34.6,1536,450.0,38.1,1539,450.3,41.3,1542,450.5,44.4,1545,450.5,48.4,1547,450.5,51.5,1549,450.5,54.6,1550,450.2,58.1,1553,449.8,60.9,1556,449.3,63.5,1562,449.3,60.7,1579,449.5,57.2,1582,450.7,53.2,1584,451.3,50.9,1587,452.0,48.7,1589,452.8,46.5,1590,453.7,43.4,1592,454.9,40.2,1593,455.8,38.1,1596,457.0,35.1,1599,457.9,33.0,1599,459.3,30.2,1602,460.7,27.7,1605,462.3,24.9,1607,464.4,23.2,1610,466.7,22.3,1613,469.8,22.1,1616,472.3,22.1,1619,475.1,23.0,1622,477.2,24.9,1624,478.8,27.4,1627,480.2,30.2,1630,481.1,33.7,1633,482.3,37.0,1636,483.0,40.4,1639,483.7,44.4,1641,483.7,47.3,1644,483.7,50.4,1647,483.7,53.6,1649,483.7,56.7,1650,483.5,59.6,1653,483.0,62.6,1656,482.1,66.0,1659,481.6,69.3,1662,481.4,71.1,1664],[523.5,34.2,1673,522.5,31.1,1683,522.1,28.8,1692,520.7,26.5,1697,518.4,25.1,1703,515.3,24.2,1706,512.3,24.2,1709,510.0,24.2,1712,507.2,25.6,1715,504.6,27.7,1717,502.1,30.0,1720,499.8,32.8,1723,497.9,35.8,1726,496.7,38.4,1729,496.0,40.9,1732,496.0,43.7,1734,496.0,46.3,1737,496.0,49.3,1740,496.7,52.3,1743,497.7,55.1,1746,498.6,58.1,1749,499.5,60.4,1752,500.7,62.8,1757,503.0,64.2,1763,505.6,64.2,1769,508.1,62.8,1772,510.2,60.9,1775,512.5,58.6,1777,514.9,55.8,1780,517.0,53.0,1783,518.6,49.8,1786,520.0,46.7,1789,520.9,43.5,1792,521.9,40.0,1794,522.5,36.7,1797,522.8,33.5,1800,523.0,30.4,1803,523.2,27.7,1806,521.6,30.4,1826,521.1,33.5,1829,520.9,37.0,1832,520.9,40.4,1834,520.9,43.9,1837,521.1,47.4,1840,521.6,50.9,1843,522.1,54.4,1846,522.5,57.7,1849,522.8,61.1,1852,522.8,64.2,1854,522.8,67.2,1857,522.8,70.0,1860,521.9,72.8,1863,520.2,75.6,1866,518.4,78.1,1869,516.0,80.2,1871,513.7,81.8,1874,511.4,83.2,1877,507.9,83.7,1880,505.6,83.7,1883,502.5,83.2,1886,500.2,81.6,1889,498.1,80.0,1891,496.3,77.9,1894,494.6,75.8,1897,494.2,75.3,1900]]},"Draw page 1":{"box":[475.8,92.8],"size":9,"ms":1700,"strokes":[[10.9,10.9,0,10.5,13.9,7,10.5,17.0,10,10.5,20.1,13,10.5,23.5,16,10.5,26.0,16,10.5,28.6,19,10.5,31.1,19,10.5,33.9,21,10.5,36.5,21,10.5,39.1,24,10.5,41.6,24,10.7,44.2,27,10.7,46.7,27,10.9,49.1,30,10.9,51.6,30,11.3,53.9,33,11.6,57.2,36,11.8,60.9,39,12.1,63.9,41,12.1,65.3,44],[9.3,11.6,53,11.8,10.2,63,14.9,10.2,66,17.7,10.2,69,20.9,10.5,72,24.4,10.9,74,28.1,11.4,77,32.1,12.1,80,36.0,13.5,83,38.9,14.9,86,41.8,16.5,88,44.4,18.2,90,47.0,20.2,91,49.4,22.1,94,51.6,23.9,97,54.2,27.0,100,56.0,30.0,102,57.0,33.5,105,57.2,37.2,108,57.0,41.1,111,55.8,44.4,114,54.6,46.5,114,53.0,48.6,117,51.4,50.9,117,49.5,53.2,120,47.4,55.3,120,45.1,57.2,122,42.8,59.1,122,40.2,60.5,125,37.7,61.6,125,35.3,62.8,128,33.0,63.7,128,30.5,64.2,131,27.9,64.6,131,24.6,64.6,134,22.3,64.6,134,19.2,64.6,136,16.3,64.6,139,12.8,64.2,142,10.0,63.2,145,7.0,62.3,148,6.5,62.1,148],[67.7,24.9,156,68.1,27.7,164,68.1,30.5,166,68.4,33.9,169,68.4,37.1,171,68.4,40.3,174,68.4,43.7,175,68.4,46.8,178,68.4,50.0,181,67.9,53.9,183,67.7,57.7,186,67.7,60.9,189,67.7,63.7,192,67.7,60.7,209,67.9,57.4,212,68.1,53.9,215,68.2,51.3,216,68.6,48.4,217,69.3,45.2,220,70.0,42.1,223,70.7,39.8,223,72.1,36.0,226,74.0,32.8,229,76.3,30.5,232,78.8,28.8,234,81.6,27.9,237,84.2,27.4,240,87.4,27.9,246,89.1,30.0,249,90.0,33.0,251],[102.3,37.0,260,103.3,34.6,289,104.9,32.8,291,107.0,31.4,297,109.3,30.2,300,111.6,29.3,305,114.2,28.8,308,117.2,28.6,314,120.0,28.6,320,122.3,29.5,328,123.7,31.4,334,124.9,33.9,342,125.6,36.5,348,125.8,39.1,354,125.8,41.6,356,125.8,44.4,362,125.8,47.0,368,125.8,49.5,373,126.0,52.1,379,126.0,54.6,385,126.5,57.2,390,126.5,59.8,399,126.7,62.6,410,126.7,60.0,436,127.0,57.2,438,127.0,54.6,444,127.0,51.8,450,126.0,49.3,455,125.1,47.0,461,122.8,45.8,467,120.0,45.8,472,117.0,45.8,478,114.2,46.3,481,111.4,47.2,487,108.4,48.6,489,105.6,50.5,495,103.3,52.1,498,101.6,53.9,504,100.7,56.3,512,100.5,58.8,518,100.7,61.6,526,102.1,63.7,535,104.6,64.6,540,107.4,64.9,546,110.7,64.6,549,114.0,63.7,555,116.5,62.8,557,119.1,61.6,560,121.4,60.5,563,123.7,59.5,566,126.5,58.4,569,128.8,57.4,574,130.2,56.7,577],[140.7,31.4,586,141.4,33.9,590,141.6,36.7,592,142.8,40.2,595,144.2,43.5,598,145.3,46.0,599,146.7,48.4,601,148.4,51.8,604,150.2,55.3,606,151.6,58.6,609,152.8,61.1,612,154.4,63.5,621,155.3,60.5,629,156.3,57.2,632,157.2,53.5,635,158.4,50.2,636,159.2,48.0,638,160.5,44.9,640,161.2,42.7,642,162.1,40.6,643,163.5,37.7,646,164.9,34.4,649,166.3,32.1,652,166.7,34.9,663,166.5,37.2,666,166.3,40.0,669,166.3,43.0,672,166.3,46.3,674,166.7,49.8,677,167.9,52.8,680,169.1,55.6,683,170.5,57.7,686,172.3,59.8,689,174.4,61.4,694,176.7,61.1,706,177.7,58.4,711,178.4,55.1,714,179.4,52.2,716,180.1,50.0,717,180.8,47.8,718,181.6,45.3,720,182.5,43.0,720,183.5,40.5,723,184.4,38.1,723,185.3,35.6,725,186.5,33.2,725,187.4,31.1,728,188.7,29.1,730,190.2,26.3,731,191.4,24.4,734],[226.0,27.2,742,224.9,30.7,752,224.6,33.7,755,224.6,37.2,758,224.6,40.9,761,224.6,44.1,764,224.9,47.0,767,225.0,49.9,768,225.3,52.8,769,225.7,55.9,772,226.0,59.1,775,226.5,63.0,778,226.7,67.0,781,227.0,70.7,783,227.0,73.7,786,227.0,76.3,789,226.5,73.2,803,226.5,70.0,806,226.3,67.1,809,226.3,64.2,812,226.3,61.8,812,226.3,58.6,815,226.3,55.3,817,226.3,53.0,817,226.3,50.7,821,226.3,47.4,822,226.3,45.1,823,226.7,41.8,826,227.4,37.9,829,228.4,34.4,832,229.8,32.1,834,231.6,30.5,837,233.7,29.1,840,236.5,28.4,843,239.1,28.4,846,241.8,28.4,849,244.4,28.6,851,246.7,30.0,854,249.1,31.6,857,251.4,33.9,860,253.5,36.5,863,255.3,39.5,866,256.7,42.6,868,257.7,45.8,871,258.1,49.3,874,258.1,52.6,877,256.7,56.0,880,254.9,58.5,883,252.8,61.1,885,250.3,63.4,887,247.9,65.1,888,244.6,66.7,891,241.4,67.2,894,238.1,67.2,897,234.9,66.5,900,232.1,64.9,903,229.3,62.3,905,227.2,59.5,908,225.3,57.0,911,223.5,54.6,914,222.8,53.5,917],[275.1,34.9,925,276.5,32.9,932,278.1,31.1,935,280.9,29.5,938,283.7,28.4,941,286.0,27.4,944,288.6,26.5,947,291.2,25.8,949,293.7,25.3,952,297.0,25.3,955,299.8,25.8,961,301.4,27.7,964,302.5,29.8,966,303.2,32.3,969,304.0,34.9,972,304.0,37.9,975,304.0,40.9,978,304.0,44.4,981,303.7,47.9,983,303.0,51.1,986,302.8,53.9,989,302.5,56.7,992,302.3,60.0,998,302.1,62.6,1000,300.9,60.0,1020,300.7,57.0,1023,300.5,54.2,1026,300.2,51.6,1029,299.8,48.8,1032,299.1,46.3,1034,298.4,43.7,1037,296.5,40.9,1043,293.7,39.5,1046,290.9,39.5,1049,287.9,40.2,1051,284.6,41.8,1054,281.6,43.5,1057,278.4,45.1,1060,275.6,47.0,1063,273.0,48.8,1065,270.7,51.4,1068,269.3,53.7,1071,268.6,56.3,1077,269.5,58.6,1080,272.3,59.3,1085,275.1,59.5,1088,278.4,59.5,1091,282.1,59.3,1094,285.0,58.8,1095,287.2,58.4,1097,290.5,57.4,1099,293.0,56.7,1099,295.6,55.8,1102,297.9,55.1,1102,300.7,54.2,1105,303.2,53.2,1105,304.4,52.8,1105],[344.2,36.7,1114,343.2,33.7,1124,342.8,31.4,1132,341.4,29.1,1138,339.1,27.7,1144,336.0,26.7,1147,333.0,26.7,1149,330.7,26.7,1152,327.9,28.1,1155,325.3,30.2,1158,322.8,32.6,1161,320.5,35.3,1164,318.6,38.4,1166,317.4,40.9,1169,316.7,43.5,1172,316.7,46.3,1175,316.7,48.8,1178,316.7,51.8,1181,317.4,54.9,1183,318.4,57.7,1186,319.3,60.7,1189,320.2,63.0,1192,321.4,65.3,1197,323.7,66.7,1203,326.3,66.7,1209,328.8,65.3,1212,330.9,63.5,1214,333.2,61.1,1217,335.6,58.4,1220,337.7,55.6,1223,339.3,52.3,1226,340.7,49.3,1229,341.6,46.0,1231,342.5,42.6,1234,343.2,39.3,1237,343.5,36.0,1240,343.7,33.0,1243,343.9,30.2,1246,342.3,33.0,1265,341.9,36.0,1268,341.6,39.5,1271,341.6,43.0,1274,341.6,46.5,1277,341.9,50.0,1280,342.3,53.5,1282,342.8,57.0,1285,343.2,60.2,1288,343.5,63.7,1291,343.5,66.7,1294,343.5,69.8,1297,343.5,72.6,1299,342.5,75.3,1302,340.9,78.1,1305,339.1,80.7,1308,336.7,82.8,1311,334.4,84.4,1314,332.1,85.8,1316,328.6,86.3,1319,326.3,86.3,1322,323.2,85.8,1325,320.9,84.2,1328,318.8,82.6,1331,317.0,80.5,1333,315.3,78.4,1336,314.9,77.9,1339],[354.6,45.3,1347,357.2,46.5,1363,360.2,46.7,1369,363.0,46.7,1372,366.0,46.3,1375,369.1,45.8,1377,372.3,45.6,1380,375.3,45.6,1383,378.6,45.6,1386,381.9,45.6,1389,384.6,45.6,1391,387.2,45.6,1394,390.0,46.0,1397,387.7,45.1,1420,385.8,43.2,1425,383.9,40.7,1428,382.5,38.4,1431,380.9,36.0,1437,379.3,33.9,1440,377.7,32.1,1442,375.3,30.0,1445,373.2,29.1,1448,370.5,28.8,1451,367.2,29.8,1454,364.6,32.1,1457,362.2,34.3,1458,360.2,37.0,1459,358.6,39.5,1462,357.2,42.1,1465,355.8,45.8,1468,355.1,49.1,1471,354.9,52.1,1474,354.9,54.4,1476,355.6,56.7,1479,357.4,58.8,1482,359.5,60.9,1485,361.9,62.8,1488,364.4,64.4,1491,367.2,65.8,1493,370.0,66.7,1496,372.8,67.9,1499,376.0,68.6,1502,379.1,69.3,1505,382.1,69.8,1508,385.1,69.8,1510,387.7,69.8,1513,389.8,68.1,1516,391.9,65.3,1519,393.2,62.7,1520,394.2,60.6,1522,395.1,58.5,1523,396.5,55.6,1525,397.4,53.5,1528,398.8,50.0,1530,400.2,46.7,1533],[432.1,21.6,1542,434.4,19.8,1569,437.2,18.8,1572,439.5,17.7,1574,441.9,16.0,1577,443.7,14.4,1580,445.6,12.8,1583,447.2,10.9,1586,449.1,8.8,1591,450.7,6.5,1594,448.8,8.6,1617,448.8,11.1,1623,450.7,13.9,1625,451.9,17.0,1628,452.5,20.0,1631,453.0,22.2,1632,453.5,24.4,1634,453.9,26.7,1637,454.1,29.2,1637,454.2,31.6,1640,454.2,34.2,1640,454.2,36.7,1642,454.2,39.5,1642,454.2,42.3,1645,454.2,45.1,1645,453.7,47.9,1648,453.5,50.5,1648,453.2,53.2,1651,453.0,55.8,1651,452.8,58.6,1654,452.8,61.1,1654,452.8,63.9,1657,452.8,66.5,1657,452.8,69.1,1659,453.2,71.6,1659,453.9,73.9,1662,454.2,74.9,1662],[437.7,69.5,1671,440.9,69.5,1683,443.9,69.5,1686,447.1,69.2,1687,450.5,68.6,1689,453.2,68.1,1692,456.0,67.9,1692,458.6,67.7,1694,461.4,67.4,1694,464.2,67.4,1697,467.0,67.4,1697,469.3,67.4,1700]]}};
  // MARK:END

  var SCALE = 0.31;        // screen pixels to a point of the recording: "Draw anything" 169 px wide
  var UNWRITE = 380;       // ms the first stroke takes them back in
  var mark = WORDS[(title.textContent || '').trim()];
  if (!mark) { hint.classList.add('is-typed'); return; }

  /* Shown already? The head's wait keeps them transparent for 1.2 s, then
   * fades them in; past that, writing them would take back words someone has
   * read. They stay, as typed (once their fade has finished, so it never
   * jumps), and the snail waits for another visit. */
  function typedShown() {
    var cs = getComputedStyle(title);
    if (cs.animationName !== 'canvas-empty-late') return false;   // no wait on this page: nothing to keep
    var m = cs.color.match(/[\d.]+/g);
    return !!m && (m.length < 4 || +m[3] > 0.05);
  }
  if (typedShown()) {
    var fading = title.getAnimations ? title.getAnimations()[0] : null;
    if (fading && fading.playState === 'running' && fading.finished) {
      fading.finished.then(function () { hint.classList.add('is-typed'); }, function () { hint.classList.add('is-typed'); });
    } else {
      hint.classList.add('is-typed');
    }
    return;
  }

  var NS = 'http://www.w3.org/2000/svg';
  var svg = document.createElementNS(NS, 'svg');
  svg.setAttribute('class', 'canvas-empty-hand');
  svg.setAttribute('viewBox', '0 0 ' + mark.box[0] + ' ' + mark.box[1]);
  svg.setAttribute('aria-hidden', 'true');
  svg.setAttribute('focusable', 'false');
  var path = document.createElementNS(NS, 'path');
  path.setAttribute('fill', 'none');
  path.setAttribute('stroke', 'currentColor');
  path.setAttribute('stroke-width', String(mark.size));
  path.setAttribute('stroke-linecap', 'round');
  path.setAttribute('stroke-linejoin', 'round');
  svg.appendChild(path);
  var said = document.createElement('span');
  said.className = 'vis-hidden';   // the typed words, kept for a screen reader, out of sight
  while (title.firstChild) said.appendChild(title.firstChild);
  title.appendChild(svg);
  title.appendChild(said);
  title.style.width = Math.round(mark.box[0] * SCALE) + 'px';
  hint.classList.add('is-hand');

  function reduce() { return !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches); }
  function r1(v) { return Math.round(v * 10) / 10; }

  /* The path as written by `at` ms: every stroke begun by then, the one under
   * way up to its pen, met between two points. A stroke of one point is a dot. */
  function written(at) {
    var out = '', S = mark.strokes;
    for (var i = 0; i < S.length; i++) {
      var s = S[i];
      if (s[2] > at) break;
      out += 'M' + s[0] + ' ' + s[1];
      if (s.length === 3) { out += 'L' + s[0] + ' ' + s[1]; continue; }
      for (var j = 3; j < s.length; j += 3) {
        if (s[j + 2] > at) {
          var k = (at - s[j - 1]) / ((s[j + 2] - s[j - 1]) || 1);
          return out + 'L' + r1(s[j - 3] + (s[j] - s[j - 3]) * k) + ' ' + r1(s[j - 2] + (s[j + 1] - s[j - 2]) * k);
        }
        out += 'L' + s[j] + ' ' + s[j + 1];
      }
    }
    return out;
  }

  var raf = 0, at = 0;
  function set(state, t) { at = t; path.setAttribute('d', t > 0 ? written(t) : ''); svg.setAttribute('data-state', state); }
  function stop() { if (raf) cancelAnimationFrame(raf); raf = 0; hint.classList.remove('is-unwriting'); }

  function write() {
    stop();
    if (reduce()) { set('done', Infinity); after(); return; }
    set('writing', 0);
    var t0 = performance.now();
    raf = requestAnimationFrame(function step(now) {
      var t = now - t0;
      if (t < mark.ms) { set('writing', t); raf = requestAnimationFrame(step); return; }
      raf = 0; set('done', Infinity); after();
    });
  }

  /* The first stroke: back to nothing in the order it came, quickest at the
   * ends, while the smaller line fades as it always has; the words' own fade
   * waits for it (styles.css, .is-unwriting). */
  function unwrite() {
    stop();
    gone();
    var from = Math.min(at, mark.ms);
    if (reduce() || !(from > 0)) { set('away', 0); return; }
    hint.classList.add('is-unwriting');
    set('unwriting', from);
    var t0 = performance.now();
    raf = requestAnimationFrame(function step(now) {
      var u = Math.min(1, (now - t0) / UNWRITE), e = u * u * (3 - 2 * u);
      set(u < 1 ? 'unwriting' : 'away', from * (1 - e));
      if (u < 1) { raf = requestAnimationFrame(step); return; }
      raf = 0; hint.classList.remove('is-unwriting');
    });
  }

  /* Under the first-open hello: blank until it has gone (lib/hello.js takes
   * itself out of the page), so the hello lifts onto words being written,
   * never onto finished ones that start over. */
  var waiting = null;
  function underHello() { return !!document.getElementById('skriblHello') && document.documentElement.hasAttribute('data-hello-comes'); }
  function start() {
    if (waiting) return;
    if (!underHello()) { write(); return; }
    set('waiting', 0);
    var h = document.getElementById('skriblHello');
    waiting = new MutationObserver(function () {
      if (document.getElementById('skriblHello')) return;
      waiting.disconnect(); waiting = null;
      if (shown) write();
    });
    waiting.observe(h.parentNode, { childList: true });
  }

  var shown = !hint.classList.contains('hidden');
  new MutationObserver(function () {
    var now = !hint.classList.contains('hidden');
    if (now === shown) return;
    shown = now;
    if (now) start();
    else {
      if (waiting) { waiting.disconnect(); waiting = null; }
      unwrite();
    }
  }).observe(hint, { attributes: true, attributeFilter: ['class'] });

  /* ---- the snail, once, in a site's post box ---- */
  // One mark each: the Pad keeps the one it has always had, Flip has its own.
  var once = document.getElementById('hintOnce'), KEY = 'skribl.once.v1' + (hint.id === 'flipEmptyHint' ? '.flip' : ''),
      player = null, began = false, shape = null;
  // Placed once the editor has laid itself out: its deferred scripts end
  // before DOMContentLoaded ('load' where that has passed), and on a slow
  // first open the Pad's canvas moved 11 px when they ran. Two frames on,
  // anything they measure in a frame has landed too.
  var settled = new Promise(function (done) {
    function go() { requestAnimationFrame(function () { requestAnimationFrame(done); }); }
    if (document.readyState === 'complete') go();
    else {
      document.addEventListener('DOMContentLoaded', go, { once: true });
      window.addEventListener('load', go, { once: true });
    }
  });
  function after() {
    if (!once || began || !shown) return;
    // A drawing that ends gone has no still picture: with Reduce Motion the
    // ball does not come, and is not spent.
    if (reduce() && ends()) return;
    // As the hello: ?once=again plays it seen or not; automation meets it
    // only when it asks (window.__skriblOnceForce), and then only once.
    if (!/[?&]once=again(&|$)/.test(location.search)) {
      if (navigator.webdriver && window.__skriblOnceForce !== true) return;
      try { if (localStorage.getItem(KEY) === '1') return; } catch (e) { return; }
    }
    began = true;
    setTimeout(function () { if (shown) begin(); }, 300);
  }
  function script(src, name) {
    if (window[name]) return Promise.resolve();
    return new Promise(function (done, fail) {
      var js = document.createElement('script');
      js.src = src;
      js.onload = function () { if (window[name]) done(); else fail(); };
      js.onerror = fail;
      document.head.appendChild(js);
    });
  }
  function begin() {
    if (!window.SkriblInline) {
      var css = document.createElement('link');
      css.rel = 'stylesheet';
      css.href = once.getAttribute('data-player-css');
      document.head.appendChild(css);
    }
    Promise.all([script(once.getAttribute('data-player-js'), 'SkriblInline'),
                 fetch(once.getAttribute('data-src')).then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); }),
                 settled])
      .then(function (got) { if (shown) play(got[1]); })
      .catch(function () {});
  }
  /* Above the words, in the room between them and the canvas's top: as wide
   * as the template asks (a share of the canvas, up to a cap), or smaller
   * where the canvas is short, and not at all where there is no room. */
  var GAP = 28;
  function place(payload) {
    var layer = once.parentNode, lr = layer.getBoundingClientRect(), tr = title.getBoundingClientRect();
    var ar = payload.canvasSize.cssHeight / payload.canvasSize.cssWidth;
    var w = Math.min(lr.width * parseFloat(once.getAttribute('data-share')), parseFloat(once.getAttribute('data-max')));
    var room = tr.top - lr.top - GAP - 8;
    if (w * ar > room) w = room / ar;
    if (w < 60) return false;
    var h = w * ar, s = once.style;
    s.width = Math.round(w) + 'px'; s.height = Math.round(h) + 'px';
    s.left = Math.round((lr.width - w) / 2) + 'px';
    s.top = Math.round(tr.top - lr.top - GAP - h) + 'px';
    return true;
  }
  function play(payload) {
    shape = payload;
    if (!place(payload)) return;
    try { localStorage.setItem(KEY, '1'); } catch (e) {}
    once.hidden = false;
    var box = once.querySelector('.skribl-inline');
    box.classList.add('is-immersive', 'is-bare');
    player = window.SkriblInline.attach(box, payload, { ambient: true });
    player.setRate(parseFloat(once.getAttribute('data-rate')) || 1);
    var p = player;
    requestAnimationFrame(function () {
      once.classList.add('is-on');
      if (reduce()) { p.seek(Infinity); return; }
      p.setLoop(false);   // once: a Flip's own loop plays inside it (the ball's three bounces)
      p.play();
      // THE BALL ENDS GONE (owner: "on last bounce it splatters into small
      // parts that disappear"): its last page is empty, and then the box
      // fades, floor and all. The player tells nobody when it ends, so ask it.
      if (ends()) {
        var watch = setInterval(function () {
          if (player !== p) { clearInterval(watch); return; }   // swept away already
          var s = p.state();
          if (s.state !== 'playing' && s.elapsedMs >= s.totalMs - 30) { clearInterval(watch); gone(); }
        }, 200);
      }
    });
    window.addEventListener('resize', replace);
  }
  function ends() { return once.getAttribute('data-end') === 'go'; }
  function replace() { if (player && !once.hidden && !place(shape)) gone(); }
  function gone() {
    if (!player) return;
    var p = player;
    player = null;
    window.removeEventListener('resize', replace);
    once.classList.remove('is-on');
    setTimeout(function () { if (p.state().state === 'playing') p.pause(); once.hidden = true; }, 300);
  }

  // Last, once everything above is defined: under Reduce Motion the words are
  // whole at once and the snail is asked for in the same breath.
  if (shown) start(); else set('away', 0);
})();
