# lula.py 💶
Artificial Intelligence for CryptoTrading - Expert of Monero  
Made with LOVE for Orange Pi 5 Max. [Python 3.9] 🐼

(Blessed by Sor. Concha) #CypherPunk

Script de instalación

1. Conéctate por SSH a tu Orange Pi: ssh -vvv root@000.000.0.0
2. Añade permisos de Ejecución: chmod +x install_lula.sh
3. Ejecútalo como SuperUsuario: sudo ./install_lula.sh

Una vez termine el script, solo tendrás que usar FileZilla para pasar tus archivos de código dentro de la carpeta lula_project que se habrá creado sola.

Test de Conexión
1. Instala las Dependencias en la Orange Pi: pip install ccxt python-dotenv
2. Ejecuta el Test: python3 connection_test.py

Entrenamiento en PC - Optimizado para Kali Linux
1. Instalar Dependencias del Sistema: sudo apt install -y python3-dev python3-pip python3-venv libxslt1-dev zlib1g-dev libgl1-mesa-glx
2. Crea un Entorno Virtual: python3 -m venv venv
3. Activa el Entorno Virtual: source venv/bin/activate
4. Instalar Dependencias: pip install -r trainer_requirements.txt
5. Ejecutar Entrenador: python trainer.py

Para obtener el .rknn final, se recomienda instalar el RKNN Toolkit 2 en un Linux x86. Con este script, ya tienes el 90% del trabajo hecho automáticamente. Si todo sale bien, el script generará directamente el archivo .rknn alimentado. Tras esto, puedes borrar el archivo .onnx que ya no vale para nada.
