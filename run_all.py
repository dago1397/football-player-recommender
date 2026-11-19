"""Ejecuta todo el pipeline: preparación -> evaluación -> imágenes.

Uso:  python run_all.py
"""
import evaluate
import figures
import prepare_data

if __name__ == "__main__":
    print("== 1/3 Preparación de datos ==")
    prepare_data.main()
    print("\n== 2/3 Evaluación Precision@20 ==")
    evaluate.main()
    print("\n== 3/3 Imágenes ==")
    figures.main()
