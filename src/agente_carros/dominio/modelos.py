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
    consumo_cidade_gasolina: float | None
    consumo_estrada_gasolina: float | None
    consumo_cidade_etanol: float | None
    consumo_estrada_etanol: float | None
    autonomia_eletrica_km: int | None
    preco_fipe: float | None
    codigo_fipe: str | None
    fonte_ficha: str

    @property
    def nome_completo(self) -> str:
        return f"{self.marca} {self.modelo} {self.versao} {self.ano}"

    @property
    def e_flex(self) -> bool:
        return self.consumo_cidade_etanol is not None and self.consumo_cidade_gasolina is not None

    @property
    def e_eletrico(self) -> bool:
        return self.combustivel.lower() == Combustivel.ELETRICO.value


@dataclass(frozen=True)
class TrechoRecuperado:
    """Um trecho de documento devolvido pela busca semantica."""

    conteudo: str
    fonte: str
    pagina: int | None = None


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
