# 🎬 Advanced Anime & Movie Video Uploader

এটি একটি সম্পূর্ণ অটোমেটেড, মডুলার পাইথন স্ক্রিপ্ট যা ভিডিও ফাইল স্ক্যান করে, অটোমেটিকভাবে মেটাডাটা (TMDB/OMDb) ফেচ করে, ভিডিওগুলো স্ট্রিমিং প্ল্যাটফর্মে (DoodStream, MixDrop, StreamTape) আপলোড করে, ইমেজগুলো Supabase Storage-এ সেভ করে এবং সমস্ত তথ্য Supabase ডাটাবেসে রেকর্ড করে।

## ✨ মূল ফিচারসমূহ

- 🎯 **স্মার্ট ফাইল পার্সিং:** ফাইলের নাম থেকে অটোমেটিক Title, Year, Season, Episode, Language এবং Quality ডিটেক্ট করে। Movie এবং TV Series আলাদা করতে সক্ষম।
- 🌐 **ডুয়াল মেটাডাটা সোর্স:** প্রথমে TMDB API থেকে মেটাডাটা খোঁজে। না পেলে অটোমেটিক fallback হিসেবে OMDb API ব্যবহার করে।
- 🖼️ **Supabase Storage ইন্টিগ্রেশন:** পোস্টার, ব্যানার এবং থাম্বনেইল সরাসরি Supabase Storage-এ অপ্টিমাইজড ফোল্ডার স্ট্রাকচারে (`{tmdb_id}/s{season}/{type}.jpg`) আপলোড করে।
- 🛡️ **আনম্যাচড ফাইল হ্যান্ডলিং:** যদি কোনো ফাইলের মেটাডাটা পাওয়া না যায়, তবে সেটি ভিডিও আপলোড না করেই একটি আলাদা `unmatched_videos` ফোল্ডারে সরিয়ে নেয়, যাতে ডাটাবেসে ভুল তথ্য না যায়।
- ⚡ **কনকারেন্ট আপলোড:** একসাথে একাধিক ফাইল প্রসেসিং এবং আপলোডের সুবিধা (Concurrency Limit কনফিগারযোগ্য)।
- 🔄 **কন্টিনিউয়াস স্ক্যানিং:** নির্দিষ্ট সময় পর পর (যেমন: ৬০ সেকেন্ড) ফোল্ডার অটোমেটিক স্ক্যান করে নতুন ফাইল খুঁজে বের করে।
- 🗂️ **সেফ আর্কাইভ:** আপলোড সফল হলে ফাইলগুলো ডিলিট না করে `archive/success` বা `archive/failed` ফোল্ডারে মুভ করে।

---

## 📋 প্রিরিকুইজিট (Prerequisites)

- Python 3.10+
- একটি সক্রিয় [Supabase](https://supabase.com/) অ্যাকাউন্ট
- [TMDB API Key](https://www.themoviedb.org/settings/api) (ফ্রি)
- [OMDb API Key](https://www.omdbapi.com/apikey.aspx) (ফ্রি, fallback-এর জন্য)
- DoodStream / MixDrop / StreamTape অ্যাকাউন্ট (যেগুলো ব্যবহার করতে চান)

---

## ⚙️ ইনস্টলেশন ও সেটআপ

### ১. রিপোজিটরি ক্লোন ও ভার্চুয়াল এনভায়রনমেন্ট তৈরি

```bash
# প্রজেক্ট ফোল্ডারে যান
cd anime-streaming-platform/backend

# ভার্চুয়াল এনভায়রনমেন্ট তৈরি ও অ্যাক্টিভেট করুন (Windows)
python -m venv venv
venv\Scripts\activate

# প্রয়োজনীয় প্যাকেজ ইনস্টল করুন
pip install -r requirements.txt
```
