import math

"""
Gabarito geodésico para o GeoAdmin Pro.

Estes valores devem ser considerados a "verdade" para validação de qualquer
implementação de cálculo no backend. Os testes podem ser importados por
outros módulos de teste (test_inverso.py, test_area.py, etc.).

Tolerâncias (Master Plan v2):
- Distâncias: ±0.001 m
- Ângulos: ±0.001 segundo de arco
"""


def assert_distancia(expected: float, computed: float, tol: float = 0.001) -> None:
  """
  Compara duas distâncias em metros dentro da tolerância permitida.
  """
  diff = abs(expected - computed)
  assert (
    diff <= tol
  ), f"Distância fora da tolerância: esperado={expected}, obtido={computed}, diff={diff}"


def assert_angulo_segundos(expected_deg: float, computed_deg: float, tol_seconds: float = 0.001) -> None:
  """
  Compara dois ângulos em graus decimais convertendo para segundos de arco.
  """
  expected_sec = expected_deg * 3600.0
  computed_sec = computed_deg * 3600.0
  diff = abs(expected_sec - computed_sec)
  assert (
    diff <= tol_seconds
  ), f"Ângulo fora da tolerância: esperado={expected_deg}°, obtido={computed_deg}°, diff_segundos={diff}"


def deg_min_sec_to_decimal(graus: int, minutos: int, segundos: float) -> float:
  sinal = 1.0
  if graus < 0:
    sinal = -1.0
    graus = abs(graus)
  return sinal * (graus + minutos / 60.0 + segundos / 3600.0)


class CasoInverso:
  def __init__(self, x1, y1, x2, y2, distancia, azimute_gms):
    self.x1 = x1
    self.y1 = y1
    self.x2 = x2
    self.y2 = y2
    self.distancia_esperada = distancia
    self.azimute_gms = azimute_gms

  @property
  def azimute_decimal_esperado(self) -> float:
    graus, minutos, segundos = self.azimute_gms
    return deg_min_sec_to_decimal(graus, minutos, segundos)


CASO_INVERSO_1 = CasoInverso(
  x1=313500.000000,
  y1=7395000.000000,
  x2=313800.000000,
  y2=7395400.000000,
  distancia=500.000000,
  # Azimute fornecido no Master Plan v2: 36°52'11.63"
  azimute_gms=(36, 52, 11.63),
)


def test_caso_inverso_placeholder():
  """
  Teste placeholder que apenas valida o próprio gabarito.

  Quando a função real de inverso for implementada no backend, crie um teste
  separado (por exemplo, em test_inverso.py) que use CASO_INVERSO_1 e asserte
  os valores retornados pela API/função.
  """
  # Verifica que o cálculo de azimute decimal a partir do gabarito está coerente.
  az_dec = CASO_INVERSO_1.azimute_decimal_esperado
  # Apenas checa que está entre 0 e 360 graus.
  assert 0.0 <= az_dec < 360.0

  # Verifica que a distância esperada é positiva.
  assert CASO_INVERSO_1.distancia_esperada > 0.0

