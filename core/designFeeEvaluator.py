# coding=utf-8
from core.apis.quickBooks.invoice import updateInvoice, createInvoice
from core.designFeeMapper import mapDesignFeeToQBAndReturn
from core.models import DesignFeeRef
from core.logger import logger


def updateDesignFeeInQB(design_fee_dict):
    designFeeDict = mapDesignFeeToQBAndReturn(design_fee_dict)
    designFeeRef = DesignFeeRef().getDesignFeeRefByTvId(design_fee_dict.get('df_id'))

    if designFeeRef:
        designFeeDict['Id'] = designFeeRef.qb_id
        updateInvoice(designFeeDict)
        logger.info('updateDesignFeeInQB | updated design fee  in qb {0}'.format(design_fee_dict))
    else:
        designFeeInQB = createInvoice(designFeeDict)
        designFeeRefObj = DesignFeeRef(
            tv_id=design_fee_dict.get('df_id'),
            qb_id=designFeeInQB.get('Invoice').get('Id')
        )
        try:
            designFeeRefObj.save()
            logger.info('updateDesignFeeInQB | created Design Fee in qb {0}'.format(design_fee_dict))
        except Exception as e:
            logger.error("updateDesignFeeInQB | Error in updateDesignFeeInQB {0}".format(design_fee_dict))
            logger.error(str(e))
    return
