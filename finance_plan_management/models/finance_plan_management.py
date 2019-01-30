from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.exceptions import except_orm, ValidationError

from dateutil.relativedelta import relativedelta
import datetime
import time
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_is_zero, float_compare
from odoo.tools.misc import formatLang

from odoo.addons.base.res.res_partner import WARNING_MESSAGE, WARNING_HELP
import odoo.addons.decimal_precision as dp


class FinancePlan(models.Model):
    _name = "finance.plan"
    _description = "Finance"


    @api.model
    def create(self, vals):
        if vals.get('name', 'Name') == 'Name':
            vals['name'] = self.env['ir.sequence'].next_by_code('finance.plan')# or '/'
        return super(FinancePlan, self).create(vals)

    name = fields.Char('Name', required=True,default='Name')
    creating_user_id = fields.Many2one('res.users', 'Prepared By', default=lambda self: self.env.user)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('cancel', 'Cancelled'),
        ('confirm', 'Confirmed'),
        ('validate', 'Validated'),
        ('done', 'Done')
        ], 'Status', default='draft', index=True, required=True, readonly=True, copy=False, track_visibility='always')
    total_cost = fields.Float('Grand Total', required=True,store=True, digits=0)
    approve_date = fields.Date('Approve Date', default = fields.Date.today())

    description = fields.Text('Description', required=False)

    shared_service_finance_lines = fields.One2many('shared.finance','shared_line_id',string='Shared Service Finance')
    cost_app_ssc = fields.One2many('cost.app.ssc','cost_app_line_id',string='Cost Apportionment')
    dummy_sum_sc = fields.Float('Total salary cost', compute='cal_sum')
    dummy_sum_total = fields.Float('Sum total cost', compute= 'cal_sum')
####$$$$

    dummy_sum_call_c = fields.Float('Total call cost', default=1,compute= 'get_total_callcostcustomer')
    dummy_sum_gadmin = fields.Float('Total Admin cost',default=1, compute= 'get_total_gadmin')
    cost_sal_total = fields.Float('Total Salary cost', default=1, compute= 'get_total_salary')
####$$$$

    cost_emp_total = fields.Float('Sum total cost', default=1, compute= 'get_total_emp')
    cost_customer_total = fields.Float('Sum Call cost', default=1, compute= 'get_total_cost')
    cost_asset_total = fields.Float('Sum Asset cost', default=1, compute= 'get_total_ass')

 ####$$$$   ####$$$$
    ####$$$$
    @api.depends('cost_app_ssc')
    def get_total_emp(self):
        for rec in self:
            total_emp = 0.0
            for ret in rec.cost_app_ssc:
                if not rec.cost_app_ssc:
                    rec.cost_emp_total = 1
                elif rec.cost_app_ssc:
                    total_emp += ret.num_employee
                    rec.cost_emp_total = total_emp

    @api.depends('cost_app_ssc')
    def get_total_cost(self):
        for rec in self:
            total_cost = 0.0
            for ret in rec.cost_app_ssc:
                total_cost += ret.num_of_customers
            rec.cost_customer_total = total_cost

    @api.depends('cost_app_ssc')
    def get_total_ass(self):
        for rec in self:
            total_ass = 0.0
            for ret in rec.cost_app_ssc:
                total_ass += ret.asset_mgt
            rec.cost_asset_total = total_ass

    @api.depends('shared_service_finance_lines')
    def get_total_salary(self):
        for rec in self:
            total_sal = 0.0
            for ret in rec.shared_service_finance_lines:
                total_sal += ret.salary_cost
            rec.cost_sal_total = total_sal

    @api.depends('shared_service_finance_lines')
    def get_total_callcostcustomer(self):
        for rec in self:
            total_costcall = 0.0
            for ret in rec.shared_service_finance_lines:
                total_costcall += ret.call_center_cost
            rec.dummy_sum_call_c = total_costcall

    @api.depends('shared_service_finance_lines')
    def get_total_gadmin(self):
        for rec in self:
            total_g= 0.0
            for ret in rec.shared_service_finance_lines:
                total_g += ret.gadmin_cost
            rec.dummy_sum_gadmin = total_g

    @api.onchange('dummy_sum_call_c','dummy_sum_gadmin','cost_sal_total')
    def grand_total(self):
        grand_total = self.dummy_sum_call_c + self.dummy_sum_gadmin + self.cost_sal_total
        self.total_cost = grand_total



    @api.depends('shared_service_finance_lines.salary_cost',
    'shared_service_finance_lines.call_center_cost',
    'shared_service_finance_lines.gadmin_cost',
    'shared_service_finance_lines.sub_total')
    def cal_sum(self):
        for rec in self:
            total_sc = 0.0
            total_cs = 0.0
            total_ga = 0.0
            total_st = 0.0
            for ret in rec.shared_service_finance_lines:
                total_sc += ret.salary_cost
                total_cs += ret.call_center_cost
                total_ga += ret.gadmin_cost
                total_st += ret.sub_total
            rec.dummy_sum_sc = total_sc
            rec.dummy_sum_call_c =total_cs
            rec.dummy_sum_gadmin = total_ga
            rec.dummy_sum_total = total_st


    @api.multi
    def confirm_budget(self):
        self.write({'state':'confirm'})
    @api.multi
    def cancel_budget(self):
        for line in self:
            line.write({'state':'cancel'})

    @api.multi
    def validate_budget(self):
        rec.state = "validate"
        rec.approve_date = fields.Date.today()

    @api.multi
    def set_draft_budget(self):
        rec.state = "draft"
    @api.multi
    def unlink(self):
        """
        Overrides orm unlink method.
        @param self: The object pointer
        @return: True/False.
        """
        if self.state in "confirm" or "validate":
            raise ValidationError('You cannot delete a confirm or validated Plan')

        return super(FinancePlan, self).unlink()

class SharedFinance(models.Model):
    _name = "shared.finance"
    _description = "Shared Budget"

    shared_line_id = fields.Many2one('finance.plan', 'Master Budget', )
    name = fields.Char('Name', required=True)
    salary_cost = fields.Float('Salaries(N)', default=0.0, digits=0)
    call_center_cost = fields.Float('Call Center Cost(N)', default=0.0, digits=0)
    gadmin_cost = fields.Float('General Admin(N)', default=0.0, digits=0)
    sub_total = fields.Float('Sub Total', default=0.0, store=True, compute='calculate_line')
    shared_line_id_link =fields.Many2one('finance.plan', 'SBU Budget', )

    @api.depends('salary_cost','call_center_cost','gadmin_cost')
    def calculate_line(self):
        for rec in self:
            total = rec.salary_cost + rec.call_center_cost + rec.gadmin_cost
            rec.sub_total = total

    #total = Add sum total

class SharedFinance(models.Model):
    _name = "cost.app.ssc"
    _description = "Ancilliary Budget"
    @api.one
    def _all_sum(self):
        for rec in self:
            get_records = self.env['cost.app.ssc'].search([])
            e = 0
            c = 0
            a = 0
            for rey in get_records:
                e += rey.num_employee
                c += rey.num_of_customers
                a += rey.asset_mgt
            rec.dummy_emp_sum = e
            rec.dummy_customer_sum = c
            rec.dummy_asset_sum = a

    cost_app_line_id = fields.Many2one('finance.plan', 'Master Budget', )
    cost_sbu_link = fields.Many2one('cost.app.ssc', 'SBU Budget', )

    name = fields.Char('SBU', required=True)
    num_employee = fields.Float('Number of Employee',store=True, default=1.0)
    num_of_customers = fields.Float('Number of Customers', store=True,default=1.0)
    asset_mgt = fields.Float('Asset Under Management', store=True,default=1.0)


############# DUMY CALCULATION
    dummy_emp_sum= fields.Float('Total employee', default=1.0,store=True)
    dummy_customer_sum= fields.Float('Total Customer',store=True, default=1.0)
    dummy_asset_sum= fields.Integer('Total Asset',store=True,)
    dummy_salary_sum= fields.Float('Total salary',default=1.0,store=True,)


#### DO COMPUTATION ON ALL USING THE COMPUTION ON XCEL SHEET
    salary_cost = fields.Float('Salaries(N)', compute='total_changes')
    call_center_cost = fields.Float('Call Center Cost(N)',store=True)#,compute='salary_main')
    gadmin_cost = fields.Float('General Admin(N)',store=True)#,compute='salary_main')
    sub_total = fields.Float('Sub Total', default=0.0, store=True,digits=0,compute='total_main')


    @api.onchange('cost_sbu_link')
    def get_number_sbu(self):
        total_sub_emp = 0.0
        total_sub_cus = 0.0
        total_sub_asset = 0.0
        for rec in self:
            for rex in rec.cost_sbu_link:
                '''total_sub_emp = rex.cost_emp_total
                total_sub_cus = rex.cost_customer_total
                total_sub_asset = rex.cost_asset_total'''
                rec.num_employee = rex.num_employee
                rec.num_of_customers=rex.num_of_customers
                rec.asset_mgt = rex.asset_mgt

    @api.onchange('cost_app_line_id.cost_emp_total','num_employee')
    def total_changes(self):
        total_sal = 0.0
        for rec in self:
            for ret in rec.cost_app_line_id:
                if ret.cost_emp_total == 0:
                    total_sal = ret.cost_sal_total * rec.num_employee
                    rec.salary_cost = total_sal/1#ret.cost_emp_total
                elif ret.cost_emp_total > 0:
                    total_sal = ret.cost_sal_total * rec.num_employee
                    rec.salary_cost = total_sal/ret.cost_emp_total

    @api.onchange('cost_app_line_id.cost_asset_total','asset_mgt')
    def total_admin_sc_changes(self):
        total_admin = 0.0
        for rec in self:
            #for ret in rec.cost_sbu_link:
            for ret in rec.cost_app_line_id:
                if ret.cost_asset_total == 0:
                    total_admin = ret.dummy_sum_gadmin * rec.asset_mgt
                    rec.gadmin_cost = total_admin/1
                elif ret.cost_asset_total > 0:
                    total_admin = ret.dummy_sum_gadmin * rec.asset_mgt
                    rec.gadmin_cost = total_admin/ret.cost_asset_total




    @api.onchange('num_of_customers','cost_app_line_id.cost_customer_total')
    def total_scot_changes(self):
        total_cost = 0.0
        for rec in self:
            for ret in rec.cost_app_line_id:
                if ret.cost_customer_total == 0:
                    total_cost = ret.dummy_sum_call_c * rec.num_of_customers
                    rec.call_center_cost = total_cost/1
                elif ret.cost_customer_total > 0:
                    total_cost = ret.dummy_sum_call_c * rec.num_of_customers
                    rec.call_center_cost = total_cost/ret.cost_customer_total

    @api.depends('salary_cost','call_center_cost','gadmin_cost')
    def total_main(self):
        for rec in self:
            rec.sub_total = rec.salary_cost + rec.call_center_cost + rec.gadmin_cost



class SBUReport_Template(models.Model):
    _name = "sbu.template.report"
    _description = "Sbu Template"
    name = fields.Char('Name')

    project_id = fields.Many2many('bed.room', string='Bed Rooms')
    land_size = fields.Float('Land Size(Sqm)', default=1.0)
    land_cost = fields.Float('Land Cost', default=1.0)
    num_of_units= fields.Float('Number of Units', default=1.0)
    duration = fields.Integer('Project Duration(Months)', default=0)
    period= fields.Selection([
        ('2018', '2018'),
        ('2019', '2019'),
        ('2020', '2020'),
        ('2021', '2021'),
        ('2022', '2022'),
        ('2023', '2023'),
        ('2024', '2023'),
        ('2025', '2025'),
        ], 'Period', default='2019', index=True, required=True, readonly=False, copy=False, track_visibility='always')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('cancel', 'Cancelled'),
        ('confirm', 'Confirmed'),
        ('validate', 'Validated'),
        ('done', 'Done')
        ], 'Status', default='draft', index=True, required=True, readonly=True, copy=False, track_visibility='always')


    total_sell_cost = fields.Float('Total sale cost',compute="get_qrts_total")
    total_labour_cost1 = fields.Float('Total Labour cost',compute="get_labour_total")
    total_sale_commission = fields.Float('Total Commission Cost ',compute="get_salecomm_total")

    total_revenue = fields.Float('Total Revenue', compute="get_revenue_qrts_total")

    total_regulatory = fields.Float('Total Regulatory', compute="get_regulatory_total")

    total_overhead = fields.Float('Total Overhead', compute="get_overheadx_total")

    total_project_cost= fields.Float('Total Project Cost', compute="get_construction_total")
    total_gross_project = fields.Float('Total Gross Project', compute="overall_grosss_main")
#######
    total_shared_cost = fields.Float('Total Shared Allocation', compute="get_SharedCost_total")
#######
    total__netsbu_project = fields.Float('Total Net SBU Profit', compute="net_sbu_profit_grandtotal")
    #####3performance_metrics
    Total_Returns = fields.Float('Total Returns', compute="calculate_total_returns")
    Return_on_investment=fields.Float('Return on Investment', compute="calculate_investment_returns")
    Profit_per_hectare = fields.Float('Profit per hectare', compute="calculate_profit_perhectare")



########### ALL LINES
    project_cost_coverage =fields. One2many('total.project.coverage', 'sbu_template_id',string='Total Cost Coverage')
    age_offplan_main_line =fields.One2many('age.offplanmain', 'sbu_template_id',string='Age OffPlan Line')
    age_finish_main_line =fields.One2many('age.finishplanmain', 'sbu_template_id',string='Age Finish Line')
    selling_price_offline =fields.One2many('selling.price.off', 'sbu_template_id',string='Selling OffPlan Line')
    selling_price_finish =fields.One2many('selling.price.finish', 'sbu_template_id',string='Selling Finish Line')

    selling_price_offline2 =fields.One2many('selling.price.off2', 'sbu_template_id',string='Calculated OffPlan Line')#,compute="get_offplan_changes")
    selling_price_finish2 =fields.One2many('selling.price.finish2', 'sbu_template_id',string='Caculated Finish Line')



    labour_headcount_line =fields.One2many('labour.headcount', 'sbu_template_id',string='Labour Headcount')
    labour_cost_line =fields.One2many('labour.costx', 'sbu_template_id',string='Labour cost')
    labour_calculate_line =fields.One2many('labour.calculates','sbu_template_id',string='Labour Details')
    revenue_offplan_line =fields.One2many('sales.revenue.offplan','sbu_template_id',string='Revenue Offplan Line')
    revenue_finish_line =fields.One2many('sales.revenue.finish','sbu_template_id',string='Revenue Finish Line')
    sbu_sale_commission_line=fields.One2many('sbu.sale.commission','sbu_template_id',string='SBU Sale Commission Line')

    construction_cost_line = fields.One2many('construction.cost','sbu_template_id',string='Construction Cost Line')
    sale_commission_line =fields.One2many('sales.commission.linexxx','sbu_template_id',string='Sale Commission Line')
    overhead_cost_line =fields.One2many('overhead.cost','sbu_template_id',string='Overhead Cost Line')
    regulatory_cost_line =fields.One2many('regulatory.cost','sbu_template_id',string='Regulatory Cost Line')


    total_projectcost_line =fields.One2many('total.net.project','sbu_template_id',string='Project Cost Line')
    total_gross_line =fields.One2many('total.gross','sbu_template_id',string='Gross Total')


    sbu_sharedcost_line =fields.One2many('shared.sbu.cost','sbu_template_id',string='SBU Cost Line')
    cashflow_opening_line =fields.One2many('cashflow.openingbalance','sbu_template_id',string='CashFlow Opening Balance Line')
    cashflow_inflow_equity_line =fields.One2many('cashflow.inflow.equity','sbu_template_id',string='Cash Inflow Equity Line')
    cashflow_inflow_loan_line =fields.One2many('cashflow.inflow.loan','sbu_template_id',string='Cash Inflow Loan Line')
    offplan_proceed_line =fields.One2many('offplan.proceeds','sbu_template_id',string='Sales Offplan Proceed Line')
    finish_proceed_line =fields.One2many('finish.proceeds','sbu_template_id',string='Sales Finish Proceed Line')
    cashflow_main_line =fields.One2many('cash.flowmain','sbu_template_id',string='Cash Flow Line')
    total_cashflow_line =fields.One2many('total.cash.outflow','sbu_template_id',string='Total Cash Flow Line')


    '''######### DEPENDS AND CHANGES ########### ##############

    @api.onchange('age_offplan_main_line')#,'selling_price_offline','project_id')
    def get_offplan_changes(self):
        room_unit = 0.0

### Get the quarters in selling price main where bed room id is == same bedroom_id
        soffquarter1 = 0.0
        soffquarter2 = 0.0
        soffquarter3 = 0.0
        soffquarter4 = 0.0
### GET PERCENTAGES OF QUARTERS IN ageoffplan line
        ageqrt1 = 0.0
        ageqrt2 = 0.0
        ageqrt3 = 0.0
        ageqrt4 = 0.0

        sale_comm = []

        for rec in self:
            selloff_price_obj =self.env['selling.price.off2']
            #idd =selloff_price_obj.search([('bed_room','=',rec.selling_price_offline2.bed_room.id)])
            for rea in rec.selling_price_offline2:
                idd =selloff_price_obj.search([('sbu_template_id','=',rea.sbu_template_id.id),('bed_room','=',rea.bed_room.id)])
                for age in rec.age_offplan_main_line:
                    if age.bed_room.id == rea.bed_room.id:
                        ageqrt1 = age.quarter1
                        ageqrt2 = age.quarter2
                        ageqrt3 = age.quarter3
                        ageqrt4 = age.quarter4
            for red in rec.project_id:
                for pro in red:
                    if pro.id == rea.bed_room.id:
                        room_unit = pro.no_unit
            for rep in rec.selling_price_offline:
                for sel1 in rep
                    if sel1.bed_room.id == rea.bed_room.id:
                        soffquarter1 = sel1.quarter1
                        soffquarter2 = sel1.quarter2
                        soffquarter3 = sel1.quarter3
                        soffquarter4 = sel1.quarter4
            quarter1 = ageqrt1 * room_unit * 100#soffquarter1
            quarter2 = ageqrt2 * room_unit * 100#soffquarter2
            quarter3 = ageqrt3 * room_unit * soffquarter3
            quarter4 = ageqrt4 * room_unit * soffquarter4
                                #bed_room_selloff2.append((6,0,{'quarter1':quarter1,'quarter2':quarter2,'quarter3':quarter3,'quarter4':quarter4}))
            #get_item = selloff_price_obj.search([('sbu_template_id','=',self.id)])
                values = {
                        'sbu_template_id':rec.id,
                        'quarter1':quarter1,
                        'quarter2':quarter2,
                        'quarter3':quarter3,
                        'quarter4':quarter4}
            #.search([('sbu_template_id','=',self.id),('bed_room','=',rec.selling_price_offline2.bed_room.id)])
                sale_comm.append((4,idd.id,{'sbu_template_id':rec.id,'quarter1':quarter1,'quarter2':quarter2,'quarter3':quarter3,'quarter4':quarter4}))
            #xx =selloff_price_obj.create({'sbu_template_id':self.id,'quarter1':quarter1,'quarter2':quarter2,'quarter3':quarter3,'quarter4':quarter4})
            rec.selling_price_offline2 =sale_comm'''
            #selloff_price_obj.write({'sbu_template_id':self.id,'quarter1':quarter1,'quarter2':quarter2,'quarter3':quarter3,'quarter4':quarter4})





            #rec.selling_price_offline2 = bed_room_selloff2

                #bed_room_ageoffplan.append(rex.bed_room.id)
            #for rez in rec.selling_price_offline2:
                #bed_room_selloff2.append(rez.bed_room.id)
            #for



    ################
    dummy_total_salesq1 = fields.Float('Total sales q1',compute="get_qrts_total")
    dummy_total_salesq2 = fields.Float('Total sales q2',compute="get_qrts_total")
    dummy_total_salesq3 = fields.Float('Total sales q3',compute="get_qrts_total")
    dummy_total_salesq4 = fields.Float('Total sales q4',compute="get_qrts_total")
    dummy_main_total_salesq1 = fields.Float('Total Sales',compute="get_qrts_total")

    dummy_total_labourq1 = fields.Float('Total labour q1',compute="get_labour_total")
    dummy_total_labourq2 = fields.Float('Total labour q2',compute="get_labour_total")
    dummy_total_labourq3 = fields.Float('Total labour q3',compute="get_labour_total")
    dummy_total_labourq4 = fields.Float('Total labour q4',compute="get_labour_total")
    dummy_main_total_labourq1 = fields.Float('Total Labour',compute="get_labour_total")


    dummy_total_revq1 = fields.Float('Total Rev q1',compute="get_revenue_qrts_total")
    dummy_total_revq2 = fields.Float('Total Rev q2',compute="get_revenue_qrts_total")
    dummy_total_revq3 = fields.Float('Total Rev q3',compute="get_revenue_qrts_total")
    dummy_total_revq4 = fields.Float('Total Rev q4',compute="get_revenue_qrts_total")
    dummy_main_total_revq1 = fields.Float('Total Revenue',compute="get_revenue_qrts_total")

#CONSTRUCTION QUARTER FIELDS
    dummy_total_proq1 = fields.Float('Total Construction q1',compute="get_construction_total")
    dummy_total_proq2 = fields.Float('Total Construction q2',compute="get_construction_total")
    dummy_total_proq3 = fields.Float('Total Construction q3',compute="get_construction_total")
    dummy_total_proq4 = fields.Float('Total Construction q4',compute="get_construction_total")
    dummy_main_total_proq1 = fields.Float('Total Construction Cost',compute="get_construction_total")


##### SAle COMMISSION QARTER FIELDS
    dummy_total_salecom1 = fields.Float('Total Commission q1',compute="get_salecomm_total")
    dummy_total_salecom2 = fields.Float('Total Commission q2',compute="get_salecomm_total")
    dummy_total_salecomq3 = fields.Float('Total Commission q3',compute="get_salecomm_total")
    dummy_total_salecomq4 = fields.Float('Total Commission q4',compute="get_salecomm_total")
    dummy_main_total_salecom = fields.Float('Total Commission Cost',compute="get_salecomm_total")

##### Overhead Quarter Fields
    dummy_total_overhead1 = fields.Float('Total overhead q1',compute="get_overheadx_total")
    dummy_total_overheadq2 = fields.Float('Total overhead q2',compute="get_overheadx_total")
    dummy_total_overheadq3 = fields.Float('Total overhead q3',compute="get_overheadx_total")
    dummy_total_overheadq4 = fields.Float('Total overhead q4',compute="get_overheadx_total")
    dummy_main_total_overhead = fields.Float('Total overhead Cost',compute="get_overheadx_total")

#### REGULARTORY QUARTER FIELDS
    dummy_total_reguq1 = fields.Float('Total Regula q1',compute="get_regulatory_total")
    dummy_total_reguq2 = fields.Float('Total Regula q2',compute="get_regulatory_total")
    dummy_total_reguq3 = fields.Float('Total Regula q3',compute="get_regulatory_total")
    dummy_total_reguq4 = fields.Float('Total Regula q4',compute="get_regulatory_total")
    dummy_main_total_regulatory= fields.Float('Total Regulatory Cost',compute="get_regulatory_total")


################### OVERALLS QRTS
    dummy_total_projectq1 = fields.Float('Total project q1', compute="totalqtrs1_overall")
    dummy_total_projectq2 = fields.Float('Total project q2',compute="totalqtrs2_overall")
    dummy_total_projectq3 = fields.Float('Total project q3',compute="totalqtrs3_overall")
    dummy_total_projectq4 = fields.Float('Total project q4',compute="totalqtrs4_overall")
    dummy_main_total_project= fields.Float('Total project Cost',compute="totalqtrs_overall")

#### GROSS QUARTER FIELDS
    dummy_total_gross1 = fields.Float('Total gross q1',compute="overall_grosss_total1")
    dummy_total_gross2 = fields.Float('Total gross q2',compute="overall_grosss_total2")
    dummy_total_gross3 = fields.Float('Total gross q3',compute="overall_grosss_total3")
    dummy_total_gross4 = fields.Float('Total gross q4',compute="overall_grosss_total4")
    dummy_main_total_gross= fields.Float('Total Gross Project Cost',compute="overall_grosss_main")

    dummy_total_ssc1 = fields.Float('Total Shared q1',compute="get_SharedCost_total")
    dummy_total_ssc2 = fields.Float('Total Shared q2',compute="get_SharedCost_total")
    dummy_total_ssc3 = fields.Float('Total Shared q3',compute="get_SharedCost_total")
    dummy_total_ssc4 = fields.Float('Total Shared q4',compute="get_SharedCost_total")
    dummy_main_total_ssc= fields.Float('Total Shared Cost',compute="get_SharedCost_total")

    dummy_total_net1 = fields.Float('Total Net Profit q1',compute="net_sbu_profit1")
    dummy_total_net2 = fields.Float('Total Net Profit q2',compute="net_sbu_profit2")
    dummy_total_net3 = fields.Float('Total Net Profit q3',compute="net_sbu_profit3")
    dummy_total_net4 = fields.Float('Total Net Profit q4',compute="net_sbu_profit4")
    dummy_main_total_net= fields.Float('Total Net Profit',compute="net_sbu_profit_grandtotal")


    @api.depends('selling_price_offline2','selling_price_finish2')
    def get_qrts_total(self):
        total1 = 0.0
        total2 = 0.0
        total3 = 0.0
        total4 = 0.0

        totalf1 = 0.0
        totalf2 = 0.0
        totalf3 = 0.0
        totalf4 = 0.0
        for rec in self:

            for rex in rec.selling_price_offline2:
                total1 += rex.quarter1
                total2 += rex.quarter2
                total3 += rex.quarter3
                total4 += rex.quarter4
            for rex in rec.selling_price_finish2:
                totalf1 += rex.quarter1
                totalf1 += rex.quarter2
                totalf1 += rex.quarter3
                totalf1 += rex.quarter4
            q1 = total1 + totalf1
            q2 = total2 + totalf2
            q3 = total3 + totalf3
            q4 = total4 + totalf4

            rec.dummy_total_salesq1 = q1
            rec.dummy_total_salesq2 = q2
            rec.dummy_total_salesq3 = q3
            rec.dummy_total_salesq4 = q4
            rec.dummy_main_total_salesq1 = q1 + q2 + q3 + q4#sum((q1,q2,q3,q4))


            rec.total_sell_cost = q1+q2+q3+q4#sum((q1,q2,q3,q4))



    @api.depends('labour_calculate_line')
    def get_labour_total(self):
        total1 = 0.0
        total2 = 0.0
        total3 = 0.0
        total4 = 0.0
        for rec in self:
            for rex in rec.labour_calculate_line:
                total1 += rex.quarter1
                total2 += rex.quarter2
                total3 += rex.quarter3
                total4 += rex.quarter4
            rec.dummy_total_labourq1 = total1
            rec.dummy_total_labourq2 = total2
            rec.dummy_total_labourq3 = total3
            rec.dummy_total_labourq4 = total4
            rec.total_labour_cost1 = total1+total2+total3+total4

    @api.depends('revenue_offplan_line','revenue_finish_line')
    def get_revenue_qrts_total(self):
        total1 = 0.0
        total2 = 0.0
        total3 = 0.0
        total4 = 0.0

        totalf1 = 0.0
        totalf2 = 0.0
        totalf3 = 0.0
        totalf4 = 0.0
        for rec in self:

            for rex in rec.revenue_offplan_line:
                total1 += rex.quarter1
                total2 += rex.quarter2
                total3 += rex.quarter3
                total4 += rex.quarter4
            for rex in rec.revenue_finish_line:
                totalf1 += rex.quarter1
                totalf1 += rex.quarter2
                totalf1 += rex.quarter3
                totalf1 += rex.quarter4
            q1 = total1 + totalf1
            q2 = total2 + totalf2
            q3 = total3 + totalf3
            q4 = total4 + totalf4

            rec.dummy_total_revq1 = q1
            rec.dummy_total_revq2 = q2
            rec.dummy_total_revq3 = q3
            rec.dummy_total_revq4 = q4
            rec.total_revenue = q1 + q2 + q3 + q4#sum((q1,q2,q3,q4))


    @api.depends('construction_cost_line')
    def get_construction_total(self):
        total1 = 0.0
        total2 = 0.0
        total3 = 0.0
        total4 = 0.0
        for rec in self:
            for rex in rec.construction_cost_line:
                total1 += rex.quarter1
                total2 += rex.quarter2
                total3 += rex.quarter3
                total4 += rex.quarter4
            rec.dummy_total_proq1 = total1
            rec.dummy_total_proq2 = total2
            rec.dummy_total_proq3 = total3
            rec.dummy_total_proq4 = total4
            rec.dummy_main_total_proq1 = total1+total2+total3+total4
            rec.total_project_cost = total1+total2+total3+total4

    @api.depends('sale_commission_line')
    def get_salecomm_total(self):
        total1 = 0.0
        total2 = 0.0
        total3 = 0.0
        total4 = 0.0
        for rec in self:
            for rex in rec.sale_commission_line:
                total1 += rex.quarter1
                total2 += rex.quarter2
                total3 += rex.quarter3
                total4 += rex.quarter4
            rec.dummy_total_salecom1 = total1
            rec.dummy_total_salecom2 = total2
            rec.dummy_total_salecomq3 = total3
            rec.dummy_total_salecomq4 = total4
            rec.dummy_main_total_salecom = total1+total2+total3+total4
            rec.total_sale_commission = total1+total2+total3+total4


    @api.depends('regulatory_cost_line')
    def get_regulatory_total(self):
        total1 = 0.0
        total2 = 0.0
        total3 = 0.0
        total4 = 0.0
        for rec in self:
            for rex in rec.regulatory_cost_line:
                total1 += rex.quarter1
                total2 += rex.quarter2
                total3 += rex.quarter3
                total4 += rex.quarter4
            rec.dummy_total_reguq1 = total1
            rec.dummy_total_reguq2 = total2
            rec.dummy_total_reguq3 = total3
            rec.dummy_total_reguq4 = total4
            rec.dummy_main_total_regulatory = total1+total2+total3+total4
            rec.total_regulatory = total1+total2+total3+total4



    @api.depends('overhead_cost_line')
    def get_overheadx_total(self):
        total1 = 0.0
        total2 = 0.0
        total3 = 0.0
        total4 = 0.0
        for rec in self:
            for rex in rec.overhead_cost_line:
                total1 += rex.quarter1
                total2 += rex.quarter2
                total3 += rex.quarter3
                total4 += rex.quarter4
            rec.dummy_total_overhead1 = total1
            rec.dummy_total_overheadq2 = total2
            rec.dummy_total_overheadq3 = total3
            rec.dummy_total_overheadq4 = total4

            rec.dummy_main_total_overhead = total1+total2+total3+total4
            rec.total_overhead = total1+total2+total3+total4



    @api.depends('dummy_total_proq1','dummy_total_reguq1','dummy_total_salecom1','dummy_total_overhead1')
    def totalqtrs1_overall(self):
        for rec in self:
            rec.dummy_total_projectq1 = rec.dummy_total_proq1 + rec.dummy_total_reguq1 + rec.dummy_total_salecom1 + rec.dummy_total_overhead1
    @api.depends('dummy_total_proq2','dummy_total_reguq2','dummy_total_salecom2','dummy_total_overheadq2')
    def totalqtrs2_overall(self):
        for rec in self:
            rec.dummy_total_projectq2 = rec.dummy_total_proq2 + rec.dummy_total_reguq2 + rec.dummy_total_overheadq2 + rec.dummy_total_salecom2
    @api.depends('dummy_total_proq3','dummy_total_reguq3','dummy_total_salecomq3','dummy_total_overheadq3')
    def totalqtrs3_overall(self):
        for rec in self:
            rec.dummy_total_projectq3 = rec.dummy_total_proq3 + rec.dummy_total_reguq3 + rec.dummy_total_overheadq3 + rec.dummy_total_salecomq3

    @api.depends('dummy_total_proq4','dummy_total_reguq4','dummy_total_salecomq4','dummy_total_overheadq4')
    def totalqtrs4_overall(self):
        for rec in self:
            rec.dummy_total_projectq4 = rec.dummy_total_proq3 + rec.dummy_total_reguq3 + rec.dummy_total_overheadq3 + rec.dummy_total_salecomq3
    @api.depends('dummy_total_projectq4','dummy_total_projectq3','dummy_total_projectq2','dummy_total_projectq1')
    def totalqtrs_overall(self):
        for rec in self:
            rec.dummy_main_total_project = rec.dummy_total_projectq4 +rec.dummy_total_projectq3 + rec.dummy_total_projectq2 + rec.dummy_total_projectq1

    @api.depends('sbu_sharedcost_line')
    def get_SharedCost_total(self):
        total1 = 0.0
        total2 = 0.0
        total3 = 0.0
        total4 = 0.0
        for rec in self:
            for rex in rec.sbu_sharedcost_line:
                total1 += rex.quarter1
                total2 += rex.quarter2
                total3 += rex.quarter3
                total4 += rex.quarter4
            rec.dummy_total_ssc1 = total1
            rec.dummy_total_ssc2 = total2
            rec.dummy_total_ssc3 = total3
            rec.dummy_total_ssc4 = total4

            rec.dummy_main_total_ssc = total1+total2+total3+total4
            rec.total_shared_cost = total1+total2+total3+total4

############ Calculate gross

    @api.depends('dummy_total_projectq1','dummy_total_revq1')
    def overall_grosss_total1(self):
        for rec in self:
            gross_amount = rec.dummy_total_revq1 - rec.dummy_total_projectq1
            rec.dummy_total_gross1 = gross_amount
    @api.depends('dummy_total_projectq2','dummy_total_revq2')
    def overall_grosss_total2(self):
        for rec in self:
            gross_amount = rec.dummy_total_revq2 - rec.dummy_total_projectq2
            rec.dummy_total_gross2 = gross_amount

    @api.depends('dummy_total_projectq3','dummy_total_revq3')
    def overall_grosss_total3(self):
        for rec in self:
            gross_amount = rec.dummy_total_revq3 - rec.dummy_total_projectq3
            rec.dummy_total_gross3 = gross_amount

    @api.depends('dummy_total_projectq4','dummy_total_revq4')
    def overall_grosss_total4(self):
        for rec in self:
            gross_amount = rec.dummy_total_revq4 - rec.dummy_total_projectq4
            rec.dummy_total_gross4 = gross_amount

    @api.depends('dummy_total_projectq2','dummy_total_revq2')
    def overall_grosss_total2(self):
        for rec in self:
            gross_amount = rec.dummy_total_revq2 - rec.dummy_total_projectq2
            rec.dummy_total_gross2 = gross_amount


    @api.depends('dummy_total_gross1','dummy_total_gross2','dummy_total_gross3','dummy_total_gross4')
    def overall_grosss_main(self):
        for rec in self:
            gross_total_amount= rec.dummy_total_gross1+rec.dummy_total_gross2+rec.dummy_total_gross3+rec.dummy_total_gross4
            rec.dummy_main_total_gross = gross_total_amount
            rec.total_gross_project =gross_total_amount

#### Calculates the quarters of Net_sbu Profit using total_dummy_qtrs - toal_dummy_sbu_qtrs
    #@api.depends('dummy_total_gross1','dummy_total_gross2','dummy_total_gross3','dummy_total_gross4')

    @api.depends('dummy_total_gross1','dummy_total_ssc1')
    def net_sbu_profit1(self):
        for rec in self:
            rec.dummy_total_net1 = rec.dummy_total_gross1 - rec.dummy_total_ssc1
    @api.depends('dummy_total_gross2','dummy_total_ssc2')
    def net_sbu_profit2(self):
        for rec in self:
            rec.dummy_total_net2 = rec.dummy_total_gross2 - rec.dummy_total_ssc2
    @api.depends('dummy_total_gross3','dummy_total_ssc3')
    def net_sbu_profit3(self):
        for rec in self:
            rec.dummy_total_net3 = rec.dummy_total_gross3 - rec.dummy_total_ssc3

    @api.depends('dummy_total_gross4','dummy_total_ssc4')
    def net_sbu_profit4(self):
        for rec in self:
            rec.dummy_total_net4 = rec.dummy_total_gross4 - rec.dummy_total_ssc4

    @api.depends('dummy_total_gross1','dummy_total_gross2','dummy_total_gross3','dummy_total_gross4')
    def net_sbu_profit_grandtotal(self):
        for rec in self:
            rec.dummy_main_total_net = rec.dummy_total_gross1 + rec.dummy_total_gross2 + rec.dummy_total_gross3 + rec.dummy_total_gross4
            rec.update({'total__netsbu_project':rec.dummy_main_total_net})
    ### CALCULATE METRICS

    ## CALCULATE TOTAL RETURNS
    @api.depends('dummy_main_total_net')
    def calculate_total_returns(self):
        for rec in self:
            rec.update({'Total_Returns':rec.dummy_main_total_net})

    ## CALCULATE RETURNS ON INVESTMENT
    @api.depends('Total_Returns','land_cost')
    def calculate_investment_returns(self):
        for rec in self:
            rec.Return_on_investment = rec.Total_Returns / rec.land_cost

    ## CALCULATE profit per hectare
    @api.depends('Total_Returns','land_size')
    def calculate_profit_perhectare(self):
        for rec in self:
            rec.Profit_per_hectare = rec.Total_Returns / rec.land_size









    @api.depends('project_id')
    def get_overhead_total(self):
        for rec in self:
            print 'Nice'

    @api.onchange('project_id')
    def get_find_units_total(self):
        for rec in self:
            total_unit =0.0

            for rex in rec.project_id:
                total_unit += rex.no_unit
            rec.num_of_units =total_unit



class Total_coverage(models.Model):
    _name = "total.project.coverage"
    _description = "Total Coverage"
    sbu_template_id = fields.Many2one('sbu.template.report','SBU Plan',required=True)
    quarter1 = fields.Float('Quarter 1')
    quarter2 = fields.Float('Quarter 2')
    quarter3 = fields.Float('Quarter 3')
    quarter4 = fields.Float('Quarter 4')

    sub_total = fields.Float('Sub Total', default=0.0, store=True, compute='calculate_line')
    @api.depends('quarter1','quarter2','quarter3','quarter4')
    def calculate_line(self):
        for rec in self:
            total = 0.0
            total_sum = rec.quarter1 + rec.quarter2 +rec.quarter3 + rec.quarter4
            total = total_sum
            rec.sub_total = total



class Bed_room(models.Model):
    _name = "bed.room"
    _description = " "
    name = fields.Char('Name')
    no_unit = fields.Float('No. of Units')
    room_price = fields.Float('Sale Price')


class Work_man(models.Model):
    _name = "work.man"
    _description = " "
    name = fields.Char('Name')

    costprice = fields.Float('Cost Price')


class Age_OffPlan(models.Model):
    _name = "ageoff.plan"
    _description = " "
    name = fields.Char('Name')
    bed_room = fields.Many2one('bed.room')

class AgeFinish_Plan(models.Model):
    _name = "agefinish.plan"
    _description = " "
    name = fields.Char('Name')
    bed_room = fields.Many2one('bed.room')


# OFF PLAN SALES Age
class ageOff_Template(models.Model):
    _name = "age.offplanmain"
    _description = "Sales/Stage Template"

    sbu_template_id = fields.Many2one('sbu.template.report','SBU Plan',required=True)
    #percent_amount = fields.Float('Percentage(%)')
    sales_amount = fields.Float('Amount')

    #age_off_id = fields.Many2one('ageoff.plan','Age Off Plan')
    bed_room = fields.Many2one('bed.room', required=True)
    quarter1 = fields.Float('Quarter 1(%)',limit=3)
    quarter2 = fields.Float('Quarter 2(%)',limit=3)
    quarter3 = fields.Float('Quarter 3(%)',limit=3)
    quarter4 = fields.Float('Quarter 4(%)', limit=3)

class ageFinish_Template(models.Model):
    _name = "age.finishplanmain"
    _description = "Sales/Stage Template"
    #age_finish_id = fields.Many2one('agefinish.plan','Age   Finish Plan')
    bed_room = fields.Many2one('bed.room',required=True)
    sbu_template_id = fields.Many2one('sbu.template.report','SBU Plan',required=True)
    #percent_amount = fields.Float('Percentage(%)')
    sales_amount = fields.Float('Total Amount')

    quarter1 = fields.Float('Quarter 1(%)', limit=3)
    quarter2 = fields.Float('Quarter 2(%)', limit=3)
    quarter3 = fields.Float('Quarter 3(%)', limit=3)
    quarter4 = fields.Float('Quarter 4(%)', limit=3)


class selling_Price_off(models.Model):
    _name = "selling.price.off"
    _description = "Selling Price"
    sbu_template_id = fields.Many2one('sbu.template.report','SBU Plan',required=True)
    bed_room = fields.Many2one('bed.room', required=True)
    agent_commssion = fields.Many2one('sbu.sale.commission','Agent Commission')
    sell_price_finish = fields.Float('Selling Price(Off Plan',related='bed_room.room_price')
    num_of_units= fields.Float('Number of Units', default=1.0)
    quarter1 = fields.Float('Quarter 1')
    quarter2 = fields.Float('Quarter 2')
    quarter3 = fields.Float('Quarter 3')
    quarter4 = fields.Float('Quarter 4')

    sub_total = fields.Float('Sub Total', default=0.0, store=True, compute='calculate_line')
    @api.depends('quarter4','quarter4','quarter4')
    def calculate_line(self):
        for rec in self:
            total = rec.quarter4 + rec.quarter4 + rec.quarter4
            rec.sub_total = total

            #search_room_id = self.env['bed.room'].search([('id','=',rec.bed_room.id)])
            #room_price = search_room_id.room_price


class selling_Price_Finish(models.Model):
    _name = "selling.price.finish"
    _description = "Selling Price Finish"

    sbu_template_id = fields.Many2one('sbu.template.report','SBU Plan',required=True)
    bed_room = fields.Many2one('bed.room',required=True)
    quarter1 = fields.Float('Quarter 1')
    quarter2 = fields.Float('Quarter 2')
    quarter3 = fields.Float('Quarter 3')
    quarter4 = fields.Float('Quarter 4')

    sub_total = fields.Float('Sub Total', default=0.0, store=True, compute='calculate_line')
    @api.depends('quarter1','quarter2','quarter3','quarter4')
    def calculate_line(self):
        for rec in self:
            total = 0.0
            total_sum = rec.quarter1 + rec.quarter2 +rec.quarter3 + rec.quarter4
            total = total_sum
            rec.sub_total = total

class selling_Price_off2(models.Model):
    _name = "selling.price.off2"
    _description = "Selling Price2"

    def get_template_id(self):
        return self.id

    sbu_template_id = fields.Many2one('sbu.template.report','SBU Plan',default=get_template_id,required=False)
    bed_room = fields.Many2one('bed.room')
    agent_commssion = fields.Many2one('sbu.sale.commission','Agent Commission')
    sell_price_finish = fields.Float('Selling Price(Off Plan',related='bed_room.room_price')
    num_of_units= fields.Float('Number of Units', default=1.0)
    quarter1 = fields.Float('Quarter 1')
    quarter2 = fields.Float('Quarter 2')
    quarter3 = fields.Float('Quarter 3')
    quarter4 = fields.Float('Quarter 4')

    sub_total = fields.Float('Sub Total', default=0.0, store=True, compute='calculate_line')


    @api.onchange('bed_room')
    def get_room_details(self):
        room_unit = 0.0

### Get the quarters in selling price main where bed room id is == same bedroom_id
        quarter1 = 0.0
        quarter2 = 0.0
        quarter3 = 0.0
        quarter4 = 0.0
### GET PERCENTAGES OF QUARTERS IN ageoffplan line
        qrt1 = 0.0
        qrt2 = 0.0
        qrt3 = 0.0
        qrt4 = 0.0

        for rec in self:

            for res in rec.sbu_template_id.project_id:

                if res.id == rec.bed_room.id:
                    room_unit = res.no_unit
            for ret in rec.sbu_template_id.selling_price_offline:

                if ret.id == rec.bed_room.id:
                    quarter1 = ret.quarter1
                    quarter2 = ret.quarter2
                    quarter3 = ret.quarter3
                    quarter4 = ret.quarter4
            for rey in rec.sbu_template_id.age_offplan_main_line:
                if rey.id == rec.bed_room.id:
                    qrt1 = rey.quarter1
                    qrt2 = rey.quarter2
                    qrt3 = rey.quarter3
                    qrt4 = rey.quarter4
            rec.quarter1 = qrt1 * room_unit * quarter1
            rec.quarter2 = qrt2 * room_unit * quarter2
            rec.quarter3 = qrt3 * room_unit * quarter3
            rec.quarter4 = qrt4 * room_unit * quarter4


    @api.depends('quarter1','quarter2','quarter3','quarter4')
    def calculate_line(self):
        for rec in self:
            total = 0.0
            total_sum = rec.quarter1 + rec.quarter2 +rec.quarter3 + rec.quarter4
            total = total_sum
            rec.sub_total = total
class selling_Price_Finish2(models.Model):
    _name = "selling.price.finish2"
    _description = "Selling Price Finish2"

    sbu_template_id = fields.Many2one('sbu.template.report','SBU Plan',required=False)
    bed_room = fields.Many2one('bed.room')
    quarter1 = fields.Float('Quarter 1' )
    quarter2 = fields.Float('Quarter 2' )
    quarter3 = fields.Float('Quarter 3' )
    quarter4 = fields.Float('Quarter 4' )

    sub_total = fields.Float('Sub Total', default=0.0, store=True, compute='calculate_line')
    @api.depends('quarter1','quarter2','quarter3','quarter4')
    def calculate_line(self):
        for rec in self:
            total = 0.0
            total_sum = rec.quarter1 + rec.quarter2 +rec.quarter3 + rec.quarter4
            total = total_sum
            rec.sub_total = total



    @api.onchange('bed_room')
    def get_room_details(self):
        room_unit = 0.0

### Get the quarters in selling price main where bed room id is == same bedroom_id
        quarter1 = 0.0
        quarter2 = 0.0
        quarter3 = 0.0
        quarter4 = 0.0
### GET PERCENTAGES OF QUARTERS IN ageoffplan line
        qrt1 = 0.0
        qrt2 = 0.0
        qrt3 = 0.0
        qrt4 = 0.0

        for rec in self:

            for res in rec.sbu_template_id.project_id:

                if res.id == rec.bed_room.id:
                    room_unit = res.no_unit
            for ret in rec.sbu_template_id.selling_price_finish:

                if ret.id == rec.bed_room.id:
                    quarter1 = ret.quarter1
                    quarter2 = ret.quarter2
                    quarter3 = ret.quarter3
                    quarter4 = ret.quarter4
            for rey in rec.sbu_template_id.age_finish_main_line:
                if rey.id == rec.bed_room.id:
                    qrt1 = rey.quarter1
                    qrt2 = rey.quarter2
                    qrt3 = rey.quarter3
                    qrt4 = rey.quarter4
            rec.quarter1 = qrt1 * room_unit * quarter1
            rec.quarter2 = qrt2 * room_unit * quarter2
            rec.quarter3 = qrt3 * room_unit * quarter3
            rec.quarter4 = qrt4 * room_unit * quarter4


class Labour_Headcount(models.Model):
    _name = "labour.headcount"
    _description = "Labour Headcount"

    sbu_template_id = fields.Many2one('sbu.template.report','Sbu Template')
    work_man_id = fields.Many2one('work.man', 'Work Man', )
    quarter1 = fields.Float('Quarter 1')
    quarter2 = fields.Float('Quarter 2')
    quarter3 = fields.Float('Quarter 3')
    quarter4 = fields.Float('Quarter 4')

    sub_total = fields.Float('Sub Total', default=0.0, store=True, compute='calculate_line')
    @api.depends('quarter1','quarter2','quarter3','quarter4')
    def calculate_line(self):
        for rec in self:
            total = 0.0
            total_sum = rec.quarter1 + rec.quarter2 +rec.quarter3 + rec.quarter4
            total = total_sum
            rec.sub_total = total
class Labour_cost(models.Model):
    _name = "labour.costx"
    _description = "Labour Cost"

    sbu_template_id = fields.Many2one('sbu.template.report','Sbu Template')
    work_man_id = fields.Many2one('work.man', 'Work Man', )
    quarter1 = fields.Float('Quarter 1')
    quarter2 = fields.Float('Quarter 2')
    quarter3 = fields.Float('Quarter 3')
    quarter4 = fields.Float('Quarter 4')

    sub_total = fields.Float('Sub Total', default=0.0, store=True, compute='calculate_line')
    @api.depends('quarter1','quarter2','quarter3','quarter4')
    def calculate_line(self):
        for rec in self:
            total = 0.0
            total_sum = rec.quarter1 + rec.quarter2 +rec.quarter3 + rec.quarter4
            total = total_sum
            rec.sub_total = total
class Labour_cost(models.Model):
    _name = "labour.calculates"
    _description = "Labour Cost"

    sbu_template_id = fields.Many2one('sbu.template.report','Sbu Template')
    work_man_id = fields.Many2one('work.man', 'Work Man', )
    quarter1 = fields.Float('Quarter 1')
    quarter2 = fields.Float('Quarter 2')
    quarter3 = fields.Float('Quarter 3')
    quarter4 = fields.Float('Quarter 4')

    sub_total = fields.Float('Sub Total', default=0.0, store=True, compute='calculate_line')

    @api.onchange('work_man_id')
    def get_recordsx(self):
        quarter1h = 0.0
        quarter2h = 0.0
        quarter3h = 0.0
        quarter4h = 0.0

        quarter1c = 0.0
        quarter2c = 0.0
        quarter3c = 0.0
        quarter4c = 0.0
        for rec in self:

            for rez in rec.sbu_template_id.labour_headcount_line:
                if rez.id == rec.work_man_id.id:
                    quarter1h=rez.quarter1
                    quarter2h=rez.quarter2
                    quarter3h=rez.quarter3
                    quarter4h=rez.quarter4
            for rev in rec.sbu_template_id.labour_cost_line:
                if rev.id == rec.work_man_id.id:
                    quarter1c=rev.quarter1
                    quarter2c=rev.quarter2
                    quarter3c=rev.quarter3
                    quarter4c=rev.quarter4
            rec.quarter1 =quarter1c * quarter1h *3
            rec.quarter2 =quarter2c * quarter2h *3
            rec.quarter3 =quarter3c* quarter3h *3
            rec.quarter4 =quarter4c* quarter4h *3

    @api.depends('quarter1','quarter2','quarter3','quarter4')
    def calculate_line(self):
        for rec in self:
            total = 0.0
            total_sum = rec.quarter1 + rec.quarter2 +rec.quarter3 + rec.quarter4
            total = total_sum
            rec.sub_total = total
class Sales_RevenueOffPlan(models.Model):
    _name = "sales.revenue.offplan"
    _description = "Sale Revenue"
    sbu_template_id = fields.Many2one('sbu.template.report','Sbu Template')
    sales_off = fields.Many2one('selling.price.off', 'Off Sales Total')
    sales_finish = fields.Many2one('selling.price.finish', 'Finished Sales Total')
    quarter1 = fields.Float('Quarter 1')
    quarter2 = fields.Float('Quarter 2')
    quarter3 = fields.Float('Quarter 3')
    quarter4 = fields.Float('Quarter 4')

    sub_total = fields.Float('Sub Total', default=0.0, store=True, compute='calculate_line')

    @api.onchange('sbu_template_id')
    def get_totals_quarter_records(self):
        for rec in self:
            tq1 = 0.0
            tq2 = 0.0
            tq3 = 0.0
            tq4 = 0.0

            tqf1 = 0.0
            tqf2 = 0.0
            tqf3 = 0.0
            tqf4 = 0.0

            for rex in rec.sbu_template_id.selling_price_offline2:
                tq1 += rex.quarter1
                tq2 += rex.quarter2
                tq3 += rex.quarter3
                tq4 += rex.quarter4

            rec.quarter1 = tq1
            rec.quarter2 = tq2
            rec.quarter3 = tq3
            rec.quarter4 = tq4

    @api.depends('quarter1','quarter2','quarter3','quarter4')
    def calculate_line(self):
        for rec in self:
            total = 0.0
            total_sum = rec.quarter1 + rec.quarter2 +rec.quarter3 + rec.quarter4
            total = total_sum
            rec.sub_total = total
class Sales_RevenueFinish(models.Model):
    _name = "sales.revenue.finish"
    _description = "Sale Revenue"
    sbu_template_id = fields.Many2one('sbu.template.report','Sbu Template')
    sales_finish = fields.Many2one('selling.price.finish', 'Finish Sales Total')
    sales_finish = fields.Many2one('selling.price.finish', 'Finished Sales Total')
    quarter1 = fields.Float('Quarter 1', compute="get_totals_quarterxxx_records")
    quarter2 = fields.Float('Quarter 2',compute="get_totals_quarterxxx_records")
    quarter3 = fields.Float('Quarter 3',compute="get_totals_quarterxxx_records")
    quarter4 = fields.Float('Quarter 4',compute="get_totals_quarterxxx_records")

    sub_total = fields.Float('Sub Total', default=0.0, store=True, compute='calculate_line')

    @api.depends('sbu_template_id')
    def get_totals_quarterxxx_records(self):
        for rec in self:
            tq1 = 0.0
            tq2 = 0.0
            tq3 = 0.0
            tq4 = 0.0

            tqf1 = 0.0
            tqf2 = 0.0
            tqf3 = 0.0
            tqf4 = 0.0

            for rex in rec.sbu_template_id.selling_price_finish2:
                tq1 += rex.quarter1
                tq2 += rex.quarter2
                tq3 += rex.quarter3
                tq4 += rex.quarter4

            rec.quarter1 = tq1
            rec.quarter2 = tq2
            rec.quarter3 = tq3
            rec.quarter4 = tq4
    @api.depends('quarter1','quarter2','quarter3','quarter4')
    def calculate_line(self):
        for rec in self:
            total = 0.0
            total_sum = rec.quarter1 + rec.quarter2 +rec.quarter3 + rec.quarter4
            total = total_sum
            rec.sub_total = total
class Sales_Sbu_Commission(models.Model):
    _name = "sbu.sale.commission"
    _description = "Cost"
    sbu_template_id = fields.Many2one('sbu.template.report','Sbu Template')
    name = fields.Char('Sales Commission')
    quarter1 = fields.Float('Quarter 1' )
    quarter2 = fields.Float('Quarter 2' )
    quarter3 = fields.Float('Quarter 3' )
    quarter4 = fields.Float('Quarter 4' )
    sub_total = fields.Float('Sub Total', default=0.0, store=True, compute='calculate_line')

    @api.depends('quarter1','quarter2','quarter3','quarter4')
    def calculate_line(self):
        for rec in self:
            total = 0.0
            total_sum = rec.quarter1 + rec.quarter2 +rec.quarter3 + rec.quarter4
            total = total_sum
            rec.sub_total = total


class ProjectConstruction_Cost(models.Model):
    _name = "construction.cost"
    _description = "Project Cost"

    sbu_template_id = fields.Many2one('sbu.template.report','Sbu Template')
    labour_hcost_id = fields.Many2one('labour.headcount ','Labour Cost')
    name = fields.Char('Description')

    construction_flow_id = fields.Many2one('total.cash.outflow','Construction Cash Outflow')
    quarter1 = fields.Float('Quarter 1',compute="get_totrecords")
    quarter2 = fields.Float('Quarter 2',compute="get_totrecords")
    quarter3 = fields.Float('Quarter 3',compute="get_totrecords")
    quarter4 = fields.Float('Quarter 4',compute="get_totrecords")

    sub_total = fields.Float('Sub Total', default=0.0, store=True, compute='calculate_line')

    @api.depends('sbu_template_id')
    def get_totrecords(self):
        for rec in self:
            tq1 = 0.0
            tq2 = 0.0
            tq3 = 0.0
            tq4 = 0.0

            for rex in rec.sbu_template_id.labour_calculate_line:
                tq1 += rex.quarter1
                tq2 += rex.quarter2
                tq3 += rex.quarter3
                tq4 += rex.quarter4

            rec.quarter1 = tq1
            rec.quarter2 = tq2
            rec.quarter3 = tq3
            rec.quarter4 = tq4

    @api.depends('quarter1','quarter2','quarter3','quarter4')
    def calculate_line(self):
        for rec in self:
            total = 0.0
            total_sum = rec.quarter1 + rec.quarter2 +rec.quarter3 + rec.quarter4
            total = total_sum
            rec.sub_total = total
class Sales_Commssion_Line(models.Model):
    _name = "sales.commission.linexxx"
    _description = "Sales Commssion Cost"

    sbu_template_id = fields.Many2one('sbu.template.report','Sbu Template')
    sale_outflow_id = fields.Many2one('total.cash.outflow','Sales Cash Outflow')

    sales_comm_id = fields.Many2one('sbu.sale.commission','Sales Commission ID')


    quarter1 = fields.Float('Quarter 1',store=True,compute='get_sale_commission')
    quarter2 = fields.Float('Quarter 2',store=True,compute='get_sale_commission')
    quarter3 = fields.Float('Quarter 3',store=True,compute='get_sale_commission')
    quarter4 = fields.Float('Quarter 4',store=True,compute='get_sale_commission')

    sub_total = fields.Float('Sub Total', default=0.0, store=True, compute='calculate_line')

    @api.depends('quarter1','quarter2','quarter3','quarter4')
    def calculate_line(self):
        for rec in self:
            total = 0.0
            total_sum = rec.quarter1 + rec.quarter2 +rec.quarter3 + rec.quarter4
            total = total_sum
            rec.sub_total = total

    @api.depends('sbu_template_id','sbu_template_id.total_sell_cost')
    def get_sale_commission(self):
        cq1 = 0.0
        cq2 = 0.0
        cq3 = 0.0
        cq4 = 0.0

        soq1 = 0.0
        soq2 = 0.0
        soq3 = 0.0
        soq4 = 0.0

        fiq1 = 0.0
        fiq2 = 0.0
        fiq3 = 0.0
        fiq4 = 0.0

        total_sale1 = 0.0
        total_sale2 = 0.0
        total_sale3 = 0.0
        total_sale4 = 0.0


        for rec in self:
            for rex in rec.sbu_template_id.sbu_sale_commission_line:
                cq1 += rex.quarter1
                cq2 += rex.quarter2
                cq3 += rex.quarter3
                cq4 += rex.quarter4
            for ret in rec.sbu_template_id.selling_price_offline2:
                soq1 += ret.quarter1
                soq2 += ret.quarter2
                soq3 += ret.quarter3
                soq4 += ret.quarter4

            for ret in rec.sbu_template_id.selling_price_finish2:
                fiq1 += ret.quarter1
                fiq2 += ret.quarter2
                fiq3 += ret.quarter3
                fiq4 += ret.quarter4

            total_sale1 = soq1 + fiq1
            total_sale2 = soq2 + fiq2
            total_sale3 = soq3 + fiq3
            total_sale4 = soq4 + fiq4

            rec.quarter1 = cq1/100 * total_sale1
            rec.quarter2= cq2/100 * total_sale2
            rec.quarter3 = cq3/100 * total_sale3
            rec.quarter4 = cq4/100 * total_sale4


class Other_Overhead(models.Model):
    _name = "overhead.cost"
    _description = "Overhead Cost"
    sbu_template_id = fields.Many2one('sbu.template.report','Sbu Template')
    overhead_flow_id = fields.Many2one('total.cash.outflow', 'Overhead Outflow')
    name = fields.Char('Description',required=True)
    quarter1 = fields.Float('Quarter 1')
    quarter2 = fields.Float('Quarter 2')
    quarter3 = fields.Float('Quarter 3')
    quarter4 = fields.Float('Quarter 4')

    sub_total = fields.Float('Sub Total', default=0.0, store=True, compute='calculate_line')

    @api.depends('quarter1','quarter2','quarter3','quarter4')
    def calculate_line(self):
        for rec in self:
            total = 0.0
            total_sum = rec.quarter1 + rec.quarter2 +rec.quarter3 + rec.quarter4
            total = total_sum
            rec.sub_total = total

class Regulatory_Cost(models.Model):
    _name = "regulatory.cost"
    _description = "Regulatory Cost"
    sbu_template_id = fields.Many2one('sbu.template.report','Sbu Template')
    name = fields.Char('Description')
    quarter1 = fields.Float('Quarter 1')
    quarter2 = fields.Float('Quarter 2')
    quarter3 = fields.Float('Quarter 3')
    quarter4 = fields.Float('Quarter 4')

    sub_total = fields.Float('Sub Total', default=0.0, store=True, compute='calculate_line')
    regulatory_flow_id = fields.Many2one('total.cash.outflow', string='Regualtory Outflow ID')

    @api.depends('quarter1','quarter2','quarter3','quarter4')
    def calculate_line(self):
        for rec in self:
            total = 0.0
            total_sum = rec.quarter1 + rec.quarter2 +rec.quarter3 + rec.quarter4
            total = total_sum
            rec.sub_total = total


class Overall_Porject_cost(models.Model):
    _name = "total.net.project"
    _description = "Overhead Cost"
    sbu_template_id = fields.Many2one('sbu.template.report','Sbu Template')
    quarter1 = fields.Float('Quarter 1')
    quarter2 = fields.Float('Quarter 2')
    quarter3 = fields.Float('Quarter 3')
    quarter4 = fields.Float('Quarter 4')
    sub_total = fields.Float('Sub Total', default=0.0, store=True, compute='calculate_line')

    @api.depends('quarter1','quarter2','quarter3','quarter4')
    def calculate_line(self):
        for rec in self:
            total = 0.0
            total_sum = rec.quarter1 + rec.quarter2 +rec.quarter3 + rec.quarter4
            total = total_sum
            rec.sub_total = total


class Gross_Total_cost(models.Model):
    _name = "total.gross"
    _description = "Overhead Cost"
    sbu_template_id = fields.Many2one('sbu.template.report','Sbu Template')
    quarter1 = fields.Float('Quarter 1')
    quarter2 = fields.Float('Quarter 2')
    quarter3 = fields.Float('Quarter 3')
    quarter4 = fields.Float('Quarter 4')
    sub_total = fields.Float('Sub Total', default=0.0, store=True, compute='calculate_line')

    @api.depends('quarter1','quarter2','quarter3','quarter4')
    def calculate_line(self):
        for rec in self:
            total = 0.0
            total_sum = rec.quarter1 + rec.quarter2 +rec.quarter3 + rec.quarter4
            total = total_sum
            rec.sub_total = total



class SharedSbuCost(models.Model):
    _name = "shared.sbu.cost"
    _description = "Shared Budget"

    sbu_template_id = fields.Many2one('sbu.template.report','Sbu Template')
    sbu_shared = fields.Many2one('shared.finance','Shared Cost')
    name = fields.Char('Description',required=True)
    quarter1 = fields.Float('Quarter 1')
    quarter2 = fields.Float('Quarter 2')
    quarter3 = fields.Float('Quarter 3')
    quarter4 = fields.Float('Quarter 4')

    sub_total = fields.Float('Sub Total', default=0.0, store=True, compute='calculate_line')
    sbu_flow_id = fields.Many2one('total.cash.outflow', 'Sbu Outflow')


    @api.depends('quarter1','quarter2','quarter3','quarter4')
    def calculate_line(self):
        for rec in self:
            total = 0.0
            total_sum = rec.quarter1 + rec.quarter2 +rec.quarter3 + rec.quarter4
            total = total_sum
            rec.sub_total = total
class cash_flowopening(models.Model):
    _name = "cashflow.openingbalance"
    _description = "Opening Balance Cost"

    sbu_template_id = fields.Many2one('sbu.template.report','Sbu Template')
    quarter1 = fields.Float('Quarter 1')
    quarter2 = fields.Float('Quarter 2')
    quarter3 = fields.Float('Quarter 3')
    quarter4 = fields.Float('Quarter 4')

    sub_total = fields.Float('Sub Total', default=0.0, store=True, compute='calculate_line')
    @api.depends('quarter1','quarter2','quarter3','quarter4')
    def calculate_line(self):
        for rec in self:
            total = 0.0
            total_sum = rec.quarter1 + rec.quarter2 +rec.quarter3 + rec.quarter4
            total = total_sum
            rec.sub_total = total

class cash_inflow(models.Model):
    _name = "cashflow.inflow.equity"
    _description = "Inflow Cost"

    sbu_template_id = fields.Many2one('sbu.template.report','Sbu Template')
    quarter1 = fields.Float('Quarter 1')
    quarter2 = fields.Float('Quarter 2')
    quarter3 = fields.Float('Quarter 3')
    quarter4 = fields.Float('Quarter 4')

    sub_total = fields.Float('Sub Total', default=0.0, store=True, compute='calculate_line')
    @api.depends('quarter1','quarter2','quarter3','quarter4')
    def calculate_line(self):
        for rec in self:
            total = 0.0
            total_sum = rec.quarter1 + rec.quarter2 +rec.quarter3 + rec.quarter4
            total = total_sum
            rec.sub_total = total

class cash_inflow(models.Model):
    _name = "cashflow.inflow.loan"
    _description = "Inflow Cost"
    sbu_template_id = fields.Many2one('sbu.template.report','Sbu Template')
    quarter1 = fields.Float('Quarter 1')
    quarter2 = fields.Float('Quarter 2')
    quarter3 = fields.Float('Quarter 3')
    quarter4 = fields.Float('Quarter 4')

    sub_total = fields.Float('Sub Total', default=0.0, store=True, compute='calculate_line')
    @api.depends('quarter1','quarter2','quarter3','quarter4')
    def calculate_line(self):
        for rec in self:
            total = 0.0
            total_sum = rec.quarter1 + rec.quarter2 +rec.quarter3 + rec.quarter4
            total = total_sum
            rec.sub_total = total

class selling_proceed_off(models.Model):
    _name = "offplan.proceeds"
    _description = "Selling Proceed"

    sbu_template_id = fields.Many2one('sbu.template.report','SBU Plan',required=True)
    bed_room = fields.Many2one('bed.room')
    agent_commssion = fields.Many2one('sbu.sale.commission','Agent Commission')
    sell_price_finish = fields.Float('Selling Price(Off Plan',related='bed_room.room_price')
    num_of_units= fields.Float('Number of Units', default=1.0)
    quarter1 = fields.Float('Quarter 1')
    quarter2 = fields.Float('Quarter 2')
    quarter3 = fields.Float('Quarter 3')
    quarter4 = fields.Float('Quarter 4')

    sub_total = fields.Float('Sub Total', default=0.0, store=True, compute='calculate_line')
    @api.depends('quarter1','quarter2','quarter3','quarter4')
    def calculate_line(self):
        for rec in self:
            total = 0.0
            total_sum = rec.quarter1 + rec.quarter2 +rec.quarter3 + rec.quarter4
            total = total_sum
            rec.sub_total = total


class selling_prfoceed_Finish(models.Model):
    _name = "finish.proceeds"
    _description = "Selling Proceed Finish"

    sbu_template_id = fields.Many2one('sbu.template.report','SBU Plan',required=True)
    bed_room = fields.Many2one('bed.room')
    quarter1 = fields.Float('Quarter 1')
    quarter2 = fields.Float('Quarter 2')
    quarter3 = fields.Float('Quarter 3')
    quarter4 = fields.Float('Quarter 4')
    sub_total = fields.Float('Sub Total', default=0.0, store=True, compute='calculate_line')

    @api.depends('quarter1','quarter2','quarter3','quarter4')
    def calculate_line(self):
        for rec in self:
            total = 0.0
            total_sum = rec.quarter1 + rec.quarter2 +rec.quarter3 + rec.quarter4
            total = total_sum
            rec.sub_total = total


class selling_prfoceed_Finish(models.Model):
    _name = "cash.flowmain"
    _description = "Selling Proceed Finish"

    sbu_template_id = fields.Many2one('sbu.template.report','SBU Plan',required=True)
    bed_room = fields.Many2one('bed.room')
    quarter1 = fields.Float('Quarter 1')
    quarter2 = fields.Float('Quarter 2')
    quarter3 = fields.Float('Quarter 3')
    quarter4 = fields.Float('Quarter 4')

    sub_total = fields.Float('Sub Total', default=0.0, store=True, compute='calculate_line')

    total_cash_outflow = fields.One2many('total.cash.outflow', 'cash_flow_id',string='Total Cash Outflow')

    @api.depends('quarter1','quarter2','quarter3','quarter4')
    def calculate_line(self):
        for rec in self:
            total = 0.0
            total_sum = rec.quarter1 + rec.quarter2 +rec.quarter3 + rec.quarter4
            total = total_sum
            rec.sub_total = total

class Total_coverage(models.Model):
    _name = "total.cash.outflow"
    _description = "Total CashOutflow"
# Must open as a form view only\
# On selection of sbu_template_id, it reads the one2many lines below and append the total of
# the lines and writes it in respective quarters

    @api.onchange('is_record')
    def get_id_lines(self):
        q1 = 0.0
        q2 = 0.0
        q3 = 0.0
        q4 = 0.0
        for rec in self:
            get_id = self.env['sbu.template.report'].search([('id','=',rec.sbu_template_id)])
            if rec.is_record == 'const':
                for rex in get_id:
                    for rex1 in rex.construction_cost_line:
                        q1 += rex1.quarter1
                        q2 += rex1.quarter2
                        q3 += rex1.quarter3
                        q4 += rex1.quarter4
                    rec.write({'quarter1':q1,'quarter2':q2,'quarter3':q3,'quarter4':q4})
            elif rec.is_record == 'sale':
                for rex in get_id:
                    for rex1 in rex.sale_commission_line:
                        q1 += rex1.quarter1
                        q2 += rex1.quarter2
                        q3 += rex1.quarter3
                        q4 += rex1.quarter4
                    rec.write({'quarter1':q1,'quarter2':q2,'quarter3':q3,'quarter4':q4})

            elif rec.is_record == 'overhead':
                for rex in get_id:
                    for rex1 in rex.overhead_cost_line:
                        q1 += rex1.quarter1
                        q2 += rex1.quarter2
                        q3 += rex1.quarter3
                        q4 += rex1.quarter4
                    rec.write({'quarter1':q1,'quarter2':q2,'quarter3':q3,'quarter4':q4})
            elif rec.is_record == 'regulate':
                for rex in get_id:
                    for rex1 in rex.regulatory_cost_line:
                        q1 += rex1.quarter1
                        q2 += rex1.quarter2
                        q3 += rex1.quarter3
                        q4 += rex1.quarter4
                    rec.write({'quarter1':q1,'quarter2':q2,'quarter3':q3,'quarter4':q4})
            elif rec.is_record == 'shared_cost':
                for rex in get_id:
                    for rex1 in rex.sbu_sharedcost_line:
                        q1 += rex1.quarter1
                        q2 += rex1.quarter2
                        q3 += rex1.quarter3
                        q4 += rex1.quarter4
                    rec.write({'quarter1':q1,'quarter2':q2,'quarter3':q3,'quarter4':q4})

    is_record = fields.Selection([
        ('const', 'Construction Cost'),
        ('sale', 'Sales Commission'),
        ('overhead', 'Overhead Cost'),
        ('regulate', 'Regulatory'),
        ('shared_cost', 'Shared')
        ], 'Status', default='const', index=True, required=True, readonly=False, copy=False, track_visibility='always')


    sbu_template_id = fields.Many2one('sbu.template.report','SBU Plan',required=True)
    quarter1 = fields.Float('Quarter 1')
    quarter2 = fields.Float('Quarter 2')
    quarter3 = fields.Float('Quarter 3')
    quarter4 = fields.Float('Quarter 4')

    sub_total = fields.Float('Sub Total', default=0.0, store=True, compute='calculate_line')

    cash_flow_id = fields.Many2one('cash.flowmain','Cash Outflow' )
    construction_cost_line = fields.Many2one('construction.cost', string='Construction Outflow')
    sales_commission_line = fields.Many2one('sales.commission.linexxx',string='Sales Commission Outflow')
    project_overhead_line = fields.Many2one('overhead.cost',string='Overhead Outflow')
    regulatory_line = fields.Many2one('regulatory.cost',string='Regulatory Outflow')
    sbu_allocation_line = fields.Many2one('shared.sbu.cost',string='SBU Cost Outflow')

    cash_flow_id = fields.Many2one('cash.flowmain','Cash Outflow' )

    '''construction_cost_line = fields.One2many('construction.cost', 'construction_flow_id',string='Construction Outflow')
    sales_commission_line = fields.One2many('sales.commission.linexxx', 'sale_outflow_id',string='Sales Commission Outflow')
    project_overhead_line = fields.One2many('overhead.cost', 'overhead_flow_id',string='Overhead Outflow')
    regulatory_line = fields.One2many('regulatory.cost', 'regulatory_flow_id',string='Regulatory Outflow')
    sbu_allocation_line = fields.One2many('shared.sbu.cost', 'sbu_flow_id',string='SBU Cost Outflow')'''

    @api.depends('quarter1','quarter2','quarter3','quarter4')
    def calculate_line(self):
        for rec in self:
            total = 0.0
            total_sum = rec.quarter1 + rec.quarter2 +rec.quarter3 + rec.quarter4
            total = total_sum
            rec.sub_total = total
