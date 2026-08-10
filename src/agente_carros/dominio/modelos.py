"""Estruturas de dados do dominio.

Estas classes nao conhecem LangChain, Streamlit, FAISS ou qualquer
provedor de LLM. Sao o vocabulario comum entre as camadas.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Combustivel(str, Enum):
    """Combustiveis suportados pela simulacao de viagem."""

    GASOLINA = "gasolina"
    ETANOL = "etanol"
    DIESEL = "diesel"
    ELETRICO = "eletrico"


@dataclass(frozen=True)
class Veiculo:
    """Uma versao especifica de um modelo, com ficha tecnica e preco.

    Os campos de consumo sao opcionais porque veiculos eletricos nao tem
    consumo em km/l e nem todo modelo aparece na tabela do Inmetro.
    """

    id: str
    marca: str
    modelo: str
    versao: str
    ano: int
    categoria: str
    motor: str
    cilindrada: float | None
    potencia_cv: int | None
    torque_kgfm: float | None
    cambio: str
    tracao: str
    portas: int
    lugares: int
    porta_malas_litros: int | None
    combustivel: str
    tanque_litros: float | None
    # Consumo do combustivel principal: gasolina nos flex e nos movidos a
    # gasolina, diesel nos movidos a diesel. Vazio nos eletricos.
    consumo_cidade: float | None
    consumo_estrada: float | None
    # Preenchidos apenas em veiculos flex.
    consumo_cidade_etanol: float | None
    consumo_estrada_etanol: float | None
    # Eficiencia dos eletricos, em km por litro equivalente de gasolina.
    consumo_cidade_kmle: float | None
    consumo_estrada_kmle: float | None
    autonomia_eletrica_km: int | None
    classe_energetica: str
    versao_pbev: str
    preco_fipe: float | None
    codigo_fipe: str | None
    mes_referencia_fipe: str
    fonte_ficha: str

    @property
    def nome_completo(self) -> str:
        return f"{self.marca} {self.modelo} {self.versao} {self.ano}"

    @property
    def e_flex(self) -> bool:
        return self.consumo_cidade_etanol is not None and self.consumo_cidade is not None

    @property
    def e_eletrico(self) -> bool:
        return self.combustivel.lower() == Combustivel.ELETRICO.value

    @property
    def tem_dados_de_consumo(self) -> bool:
        return self.consumo_cidade is not None and self.consumo_estrada is not None


@dataclass(frozen=True)
class TrechoRecuperado:
    """Um trecho de documento devolvido pela busca semantica."""

    conteudo: str
    fonte: str
    pagina: int | None = None


@dataclass(frozen=True)
class PrecoCombustivel:
    """Preco de um combustivel num estado, apurado pela ANP."""

    uf: str
    produto: str
    preco_mediano: float
    preco_minimo: float
    preco_maximo: float
    amostras: int
    periodo_inicio: str
    periodo_fim: str

    @property
    def descricao_periodo(self) -> str:
        return f"levantamento da ANP de {self.periodo_inicio} a {self.periodo_fim}"


@dataclass(frozen=True)
class CustoPorCombustivel:
    """Resultado da simulacao para um combustivel especifico."""

    combustivel: str
    consumo_medio_km_l: float
    litros_necessarios: float
    preco_por_litro: float
    custo_total: float
    custo_por_km: float
    abastecimentos_necessarios: float | None


@dataclass(frozen=True)
class ResultadoViagem:
    """Resultado completo de uma simulacao de viagem."""

    veiculo: str
    distancia_km: float
    proporcao_cidade: float
    proporcao_estrada: float
    ida_e_volta: bool
    custos: list[CustoPorCombustivel]
    observacoes: list[str]

    @property
    def mais_economico(self) -> CustoPorCombustivel | None:
        return min(self.custos, key=lambda c: c.custo_total) if self.custos else None
