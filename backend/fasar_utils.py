class FasarEngine:
    def __init__(self, uma_2026=115.50, risk_premium=7.58875):
        # 2026 Estimated UMA and Construction Risk Grade V
        self.uma = uma_2026
        self.risk_premium = risk_premium / 100 
        
    def calculate_fasar(self, base_salary: float):
        # Integration Factor (15 days Aguinaldo + 12 days Vacation @ 25% Premium)
        integration_factor = 1.0493 
        sdi = base_salary * integration_factor
        
        # IMSS Employer Quotas (2026 Law Compliance)
        fixed_quota = self.uma * 0.2040
        exceeding_quota = max(0, (sdi - (3 * self.uma)) * 0.0110)
        pension_and_life = sdi * 0.0175
        guardianship = sdi * 0.0100
        infonavit = sdi * 0.0500
        retirement = sdi * 0.0200
        
        # Occupational Risk (Prima de Riesgo)
        risk_cost = sdi * self.risk_premium
        
        total_employer_cost = (sdi + fixed_quota + exceeding_quota + 
                               pension_and_life + guardianship + 
                               infonavit + retirement + risk_cost)
        
        # The Factor (Total Cost / Base Salary)
        fasar = total_employer_cost / base_salary
        return round(fasar, 4), round(total_employer_cost, 2)