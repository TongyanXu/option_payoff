# coding=utf-8
"""definition of stock for payoff estimation and pricing"""

from instrument import Instrument
# from instrument.env_param import EnvParam
# from numpy.ma import exp


class Stock(Instrument):
    """stock class with basic parameters"""
    _name = "stock"

    def __init__(self, inst_dict_):
        super(Stock, self).__init__(inst_dict_)
        self.price = self.isp

    def payoff(self, spot_):
        """get stock payoff for given spot"""
        return spot_ * self.unit

    def pv(self, mkt_dict_, engine_, overwrite_isp_=None):
        """no pv calc needed for stock"""
        # _div, _t = tuple(self._load_market(mkt_dict_, [EnvParam.UdDivYieldRatio.value, EnvParam.PortMaturity.value]))
        _base = overwrite_isp_ if overwrite_isp_ else self.isp
        return _base  # * exp(-_div * _t)

    def delta(self, mkt_dict_, engine_, overwrite_isp_=None):
        """no delta calc needed for stock"""
        return 1

    def gamma(self, mkt_dict_, engine_, overwrite_isp_=None):
        """no gamma calc needed for stock"""
        return 0
