# coding=utf-8
"""definition of option for payoff estimation and pricing"""

from numpy import average
from numpy.ma import exp, log, sqrt
from scipy.stats import norm
from instrument import InstParam, InstType, Instrument, option_type
from instrument.env_param import EngineMethod, EngineParam, EnvParam, RateFormat
from utils import to_continuous_rate


class Option(Instrument):
    """
    option class with basic parameters
    only vanilla option is available (barrier is not supported)
    can estimate option payoff under different level of spot
    can evaluate option price under different market using different evaluation engine
    """
    _name = "option"
    _strike = None
    _maturity = None

    def __init__(self, inst_dict_):
        super(Option, self).__init__(inst_dict_)
        self.strike = inst_dict_.get(InstParam.OptionStrike.value)
        self.maturity = inst_dict_.get(InstParam.OptionMaturity.value)

    def __str__(self):
        return "{} * {} {}, Maturity {}".format(self.unit, self.strike, self.type, self.maturity)

    def payoff(self, spot_):
        """get option payoff for given spot"""
        _reference = spot_ - self.strike if self.type == InstType.CallOption.value else self.strike - spot_
        return max([_reference, 0]) * self.unit

    def pv(self, mkt_dict_, engine_, overwrite_isp_=None):
        """calculate option PV with market data and engine"""
        _rate, _vol, _div = self._load_market(mkt_dict_)
        _method, _param = self._load_engine(engine_)
        _sign = 1 if self.type == InstType.CallOption.value else -1
        _isp = overwrite_isp_ if overwrite_isp_ else self.isp

        if _method == EngineMethod.BS.value:
            _d1 = (log(_isp / self.strike) + (_rate + _vol ** 2 / 2) * self.maturity) / _vol / sqrt(self.maturity)
            _d2 = _d1 - _vol * sqrt(self.maturity)
            return _sign * (_isp * exp(-_div * self.maturity) * norm.cdf(_sign * _d1) -
                            self.strike * exp(-_rate * self.maturity) * norm.cdf(_sign * _d2))

        elif _method == EngineMethod.MC.value:
            from utils.monte_carlo import MonteCarlo
            _iteration = _param.get(EngineParam.MCIteration.value)
            if not _iteration:
                raise ValueError("iteration not specified")
            if not isinstance(_iteration, int):
                raise ValueError("type <int> is required for iteration, not {}".format(type(_iteration)))
            _spot = MonteCarlo.stock_price(_iteration, isp=_isp, rate=_rate, div=_div, vol=_vol, maturity=self.maturity)
            _price = [max(_sign * (_s - self.strike), 0) for _s in _spot]
            return average(_price) * exp(-_rate * self.maturity)

    def delta(self, mkt_dict_, engine_, overwrite_isp_=None):
        """calculate option DELTA with market data and engine"""
        _rate, _vol, _div = self._load_market(mkt_dict_)
        _method, _param = self._load_engine(engine_)
        _sign = 1 if self.type == InstType.CallOption.value else -1
        _isp = overwrite_isp_ if overwrite_isp_ else self.isp

        if _method == EngineMethod.BS.value:
            _d1 = (log(_isp / self.strike) + (_rate + _vol ** 2 / 2) * self.maturity) / _vol / sqrt(self.maturity)
            return _sign * norm.cdf(_sign * _d1)

        elif _method == EngineMethod.MC.value:
            from utils.monte_carlo import MonteCarlo
            _iteration = _param.get(EngineParam.MCIteration.value)
            if not _iteration:
                raise ValueError("iteration not specified")
            if not isinstance(_iteration, int):
                raise ValueError("type <int> is required for iteration, not {}".format(type(_iteration)))
            _spot = MonteCarlo.stock_price(_iteration, isp=_isp, rate=_rate, div=_div, vol=_vol, maturity=self.maturity)
            _step = 0.01
            _delta = [(max(_sign * (_s + _step - self.strike), 0) - max(_sign * (_s - _step - self.strike), 0)) /
                      (_step * 2) for _s in _spot]
            return average(_delta) * exp(-_rate * self.maturity)

    @property
    def type(self):
        """option type - CALL or PUT"""
        if self._type is None:
            raise ValueError("{} type not specified".format(self._name))
        return self._type

    @type.setter
    def type(self, type_):
        if type_ not in option_type:
            raise ValueError("invalid {} type given".format(self._name))
        self._type = type_

    @property
    def strike(self):
        """strike level - percentage of ISP"""
        if self._strike is None:
            raise ValueError("strike level not specified")
        return self._strike

    @strike.setter
    def strike(self, strike_):
        if not isinstance(strike_, float) and not isinstance(strike_, int):
            raise ValueError("type <int> or <float> is required for strike level, not {}".format(type(strike_)))
        self._strike = strike_

    @property
    def maturity(self):
        """option maturity - year"""
        if self._maturity is None:
            raise ValueError("maturity not specified")
        return self._maturity

    @maturity.setter
    def maturity(self, maturity_):
        if maturity_ is not None:
            if not isinstance(maturity_, (int, float)):
                raise ValueError("type <int> or <float> is required for maturity, not {}".format(type(maturity_)))
            if maturity_ < 0:
                raise ValueError("non-negative value is required for maturity, not {}".format(maturity_))
            self._maturity = maturity_

    @staticmethod
    def _load_market(mkt_dict_):
        _rate = mkt_dict_.get(EnvParam.RiskFreeRate.value) / 100
        if not isinstance(_rate, (int, float)):
            raise ValueError("type <int> or <float> is required for market risk free rate, not {}".format(type(_rate)))
        _vol = mkt_dict_.get(EnvParam.UdVolatility.value) / 100
        if not isinstance(_vol, (int, float)):
            raise ValueError("type <int> or <float> is required for underlying volatility, not {}".format(type(_vol)))
        _div = mkt_dict_.get(EnvParam.UdDivYieldRatio.value) / 100
        if not isinstance(_div, (int, float)):
            raise ValueError("type <int> or <float> is required for dividend yield ratio, not {}".format(type(_div)))
        _rate_format = mkt_dict_.get(EnvParam.RateFormat.value)
        if _rate_format not in [_r.value for _r in RateFormat]:
            raise ValueError("invalid rate type given: {}".format(_rate_format))
        if _rate_format == RateFormat.Single.value:
            _rate = to_continuous_rate(_rate)
            _div = to_continuous_rate(_div)
        return _rate, _vol, _div

    @staticmethod
    def _load_engine(engine_):
        _method = engine_.get('engine')
        if _method not in [_m.value for _m in EngineMethod]:
            raise ValueError("invalid evaluation engine given: {}".format(_method))
        _param = engine_.get('param', {})
        return _method, _param


if __name__ == '__main__':
    import sys
    sys.path.append("/Users/Tongyan/Desktop/python_project/")

    from personal_utils.logger_utils import get_default_logger
    from personal_utils.time_utils import Timer

    logger = get_default_logger("option pricing test")

    callput = InstType.CallOption.value
    strike = 80
    spot = 100
    maturity = 1
    rate = 2
    vol = 5
    iteration = 1000000

    inst_1 = {
        InstParam.InstType.value: callput,
        InstParam.OptionStrike.value: strike,
        InstParam.OptionMaturity.value: maturity
    }

    mkt = {
        EnvParam.RiskFreeRate.value: rate,
        EnvParam.UdVolatility.value: vol
    }

    engine_1 = dict(engine=EngineMethod.BS.value)
    engine_2 = dict(engine=EngineMethod.MC.value, param={EngineParam.MCIteration.value: iteration})

    option_1 = Instrument.get_inst(inst_1)

    _timer = Timer("option pricing: {} {}, {} years, rate {}%, vol {}%".format(
        strike, "call" if callput == InstType.CallOption.value else "put", maturity, rate, vol), logger, rounding_=6)
    price_bs = round(option_1.pv(mkt, engine_1), 6)
    logger.info("price = {} (Black-Scholes)".format(price_bs))
    _timer.mark("pricing using Black-Scholes")
    price_mc = round(option_1.pv(mkt, engine_2), 6)
    logger.info("price = {} (Monte-Carlo, {} iteration)".format(price_mc, iteration))
    _timer.mark("pricing using Monte-Carlo with {} iteration".format(iteration))
    _timer.close()

    option_1.price = price_bs
    option_1.unit = 1
    logger.info("option payoff at spot {}: {}".format(spot, round(option_1.payoff(spot), 6)))
