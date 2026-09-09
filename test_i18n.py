from utils.i18n import load_translations, tr

def test_localization():
    print("Loading translations...")
    load_translations("locales")
    
    print("\nTesting English (default):")
    print(f"Welcome: {tr('welcome', 'en')}")
    print(f"Error: {tr('error_generic', 'en', error='Something went wrong')}")
    
    print("\nTesting French:")
    print(f"Welcome: {tr('welcome', 'fr')}")
    print(f"Error: {tr('error_generic', 'fr', error='Quelque chose a mal tourné')}")
    
    print("\nTesting Russian:")
    print(f"Welcome: {tr('welcome', 'ru')}")
    print(f"Error: {tr('error_generic', 'ru', error='Что-то пошло не так')}")

    print("\nTesting Missing Key (should fallback to key):")
    print(f"Missing: {tr('non_existent_key', 'en')}")

if __name__ == "__main__":
    test_localization()
