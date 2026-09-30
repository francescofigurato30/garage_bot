import os
import django

# Inizializza l'ambiente Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from bot.engine import handle_incoming_message

def run_chat():
    print("=" * 55)
    print("🤖 SIMULATORE CHATBOT GARAGE (scrivi 'esci' per uscire)")
    print("=" * 55)
    
    # ID utente di prova
    test_wa_id = "+393331234567"
    
    # Simula il primo messaggio "ciao"
    welcome = handle_incoming_message(test_wa_id, "ciao", user_name="Francesco")
    print(f"\n[BOT]:\n{welcome}\n")
    
    while True:
        user_input = input("[TU]: ")
        if user_input.strip().lower() in ['esci', 'exit', 'quit']:
            print("Arrivederci!")
            break
        if not user_input.strip():
            continue
            
        reply = handle_incoming_message(test_wa_id, user_input)
        print(f"\n[BOT]:\n{reply}\n")

if __name__ == '__main__':
    run_chat()
    