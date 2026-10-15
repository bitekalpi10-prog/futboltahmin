# FutbolTahmin — Web sitesi kurulum paketi

Bu paket, Flask tabanlı bir futbol haftalık bülten sitesi içerir. Gerçek maç verileri için Football-Data.org API anahtarı gerekir.

## En kolay yayınlama: Render + GitHub
1. Ücretsiz Football-Data.org hesabı aç: https://www.football-data.org/client/register
2. Bu ZIP'i çıkar ve dosyaları yeni bir GitHub deposuna yükle.
3. Render'a gir: https://render.com/ ve GitHub hesabını bağla.
4. Render Dashboard → New → Blueprint (veya Web Service) ile depoyu seç. `render.yaml` otomatik ayarları içerir.
5. Render servisinin Environment bölümünde `FOOTBALL_DATA_TOKEN` anahtarı ekle ve API token'ını değer olarak gir. Anahtarı asla HTML/JavaScript içine koyma.
6. Deploy tamamlanınca Render sana `https://...onrender.com` biçiminde bir adres verir. Siteyi bu adresle bilgisayar ve telefondan açabilirsin.
7. GitHub deposu Settings → Secrets and variables → Actions → New repository secret bölümüne `FOOTBALL_DATA_TOKEN` ekle. Actions sekmesinde haftalık iş akışının etkin olduğunu kontrol et. İstersen `Run workflow` ile elle başlat.

## Yerelde deneme (Windows)
Python 3.11+ kur. Proje klasöründe PowerShell aç:
```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:FOOTBALL_DATA_TOKEN="API_TOKENIN"
python refresh.py
python app.py
```
Sonra http://127.0.0.1:5000 adresini aç.

## Veri kapsamı ve önemli sınırlar
- Varsayılan ligler: Premier League, La Liga, Serie A, Bundesliga ve Ligue 1.
- Football-Data.org ücretsiz kapsamı Türkiye Süper Lig'i garanti etmez; Süper Lig için ayrı bir sağlayıcı/plan gerekebilir.
- Ücretsiz API katmanında istek sınırları ve veri gecikmesi olabilir.
- Render ücretsiz web servisleri boşta kaldığında uykuya geçebilir ve yerel dosya değişiklikleri yeniden başlatma/deploy sırasında kaybolabilir. Bu yüzden haftalık JSON güncellemesi GitHub'da saklanır; canlı uygulamada JSON dosyasının otomatik güncel kopyasını kullanmak için kalıcı depolama veya başlangıçta depodan çekme entegrasyonu gerekebilir.
- Render web uygulamasını barındırır; GitHub Actions haftalık veriyi günceller. Bunlar iki ayrı hizmettir.
- Tahminler basit Poisson modeli kullanır ve garanti değildir. Sakatlık, kadro, xG ve ev/deplasman ayrımı modelde henüz tam ele alınmaz.
- Herkese açık dağıtımda `/api/refresh` uç noktasına kimlik doğrulaması ekle veya bu uç noktayı kapat.
