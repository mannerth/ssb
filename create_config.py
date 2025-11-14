import json
import os


def create_formula_descriptions():
    """创建公式描述配置文件"""
    data = {
        #1、热源厂采暖季热单耗
                    "热源厂采暖季热单耗":"""
                        公式：q = (Q(t=end) - Q(t=start)) / A * 24 * 120 / ((t=end - t=start) + 1)

                    公式描述：
                        采暖季内，整个供热系统的单位建筑面积或单位供热量所消耗的热量，用于衡量供热系统的能源利用效率和节能水平。
                        用采暖季结束时的累计热量 减去 采暖季开始时的累计热量 结果除以 整个热网总供热面积。 
                    
                    公式中参数含义：
                        q：水网单位面积热单耗（单位：GJ/㎡·季）；
                        Q(t=end) ：热源采暖季结束时的累计热量（单位：GJ，时间为次年3月15日 0:00）；
                        Q(t=start) ：热源采暖季起始时的累计热量（单位：GJ，时间为当年11月15日 0:00）；
			            (Q(t=end) - Q(t=start))：热源厂采暖季的总耗热量/产热量/累计热量；
                        A：热网总供热面积（单位：㎡）；
			            (t=end - t=start)：结束时间和起始时间的时间段内小时数；
                        
                    数据库对应字段：
                        Q：ods_sc01_ntjt_zhgr_heat_source_inst_data表中src_id分别为1和2的src_sup _total_hheat；src_id=1的是商河恒泰热源厂，src_id=2是玉泉生物质电厂，若未明确指出哪个热源厂的指标计算，那么热源厂热单耗需要计算两个热源总和的热单耗，总热量需要分别计算src_id为1和2的累计热量的差值，再汇总得到热源厂总热量；因为不同热源src_id的数据data_time不相同，统计热量时不同src_id要分别获取起始时间和结束时间；
                        A：ods_sc01_ntjt_zhgr_heat_station_info表中所有stn_id的heat_area之和；
			
                                            """,
                    #2 热源厂指定时段热单耗
                    "查询热源厂指定时段热单耗":"""
                    公式：q = (Q(t=end) - Q(t=start)) / A × (24 × 120) / ((t=end - t=start) + 1)

                    公式描述： 
                    步骤一：指定时段热单耗，是通过结束时间累计热量 - 起始时间累计热量的结果，除以问题热源厂的总供热面积。 
                    步骤二：步骤一结果要转换成采暖季量级，需要将上述结果，按照小时粒度，计算从开始时间到结束时间有多少小时。并将步骤一结果除以小时数，在乘以24（每天的小时数）和 120（采暖季的天数）
                    #要记住!!，只有做了步骤二，生成的热单耗单位才是：GJ/㎡·季， 如果没有做步骤二，单位是：GJ/㎡


                    公式中参数含义：
                        q：水网单位面积热单耗（单位：GJ/㎡·季）；
                        Q(t=end) ：热源采暖季结束时的累计热量（单位：GJ）；
                        Q(t=start) ：热源采暖季起始时的累计热量（单位：GJ）；
                        A：热网总供热面积（单位：㎡）；
                        (t=end - t=start)：指定时段时间长度（单位：小时H）；
		                (Q(t=end) - Q(t=start))：热源厂采暖季的总耗热量/产热量/累计热量；
                        t：时间；

                    数据库对应字段：
                        Q：ods_sc01_ntjt_zhgr_heat_source_inst_data表中src_id分别为1和2的src_sup _total_hheat；src_id=1的是商河恒泰热源厂，src_id=2是玉泉生物质电厂，若未明确指出哪个热源厂的指标计算，那么热源厂热单耗需要计算两个热源总和的热单耗，总热量需要分别计算src_id为1和2的累计热量的差值，再汇总得到热源厂总热量；因为不同热源src_id的数据data_time不相同，统计热量时不同src_id要分别获取起始时间和结束时间；
                        A：ods_sc01_ntjt_zhgr_heat_station_info表中所有stn_id的heat_area之和；

                    """,
                    #3、换热站采暖季热单耗
                    "查询指定换热站采暖季热单耗":"""

                        公式：qₐ = (Qₐ(t=end) - Qₐ(t=start)) / Aₐ * 24 * 120 / ((t=end - t=start) + 1)
                        公式中参数含义：
                            qₐ：换热站a采暖季单位面积热单耗（单位： GJ/m²·季）；
                            Qₐ(t=end)：换热站a采暖季结束时的一次侧累计热量（单位：GJ，时间为次年3月15日 0:00）；
                            Qₐ(t=start)：换热站a采暖季开始时的一次侧累计热量（单位：GJ，时间为当年11月15日 0:00）；
                            Aₐ：换热站a供热面积（单位：m²）；
                            t：时间；
			                (t=end - t=start)：起始时间和结束时间之间的小时数；
                            
                        公式描述：采暖季内，某一换热站的单位建筑面积或单位供热量所消耗的热量，用于衡量供热系统的能源利用效率和节能水平。
                            
                        公式中的参数在数据库对应的字段：
                            Qₐ：ods_sc01_ntjt_zhgr_heat_station_inst_data表stn_id为a的stn_prim_total_hheat；
                            Aₐ：ods_sc01_ntjt_zhgr_heat_station_info表stn_id为a的heat_area；
                            t：ods_sc01_ntjt_zhgr_heat_station_inst_data表data_time；     

                            """,
                    #4、换热站指定时段热单耗
                    "查询换热站指定时段热单耗": """

                        公式：qₐ = [(Qₐ(t=end) - Qₐ(t=start)) / Aₐ] × (24 × 120) / ((t=end - t=start) + 1)
                        
                        公式中参数含义：
                            qₐ：换热站a指定时段内单位面积热单耗（单位： GJ/m²·季）；
                            Qₐ(t=end)：换热站a指定时段结束时间的一次侧累计热量（单位：GJ）；
                            Qₐ(t=start)：换热站a指定时段起始时间的一次侧累计热量（单位：GJ）；
                            Aₐ：换热站a供热面积（单位：m²）；
                            (t=end - t=start)：指定时段时间长度（单位：小时H）；
                            t：时间；
                            
                        公式描述：
                            采暖季的某一段时间，某一换热站的单位建筑面积或单位供热量所消耗的热量，用于衡量供热系统的能源利用效率和节能水平。
                            
                        
                        公式中的参数在数据库对应的字段：
                            Qₐ：ods_sc01_ntjt_zhgr_heat_station_inst_data表stn_id为a的stn_prim_total_hheat；
                            Aₐ：ods_sc01_ntjt_zhgr_heat_station_info表stn_id为a的heat_area；
                            t：ods_sc01_ntjt_zhgr_heat_station_inst_data表data_time；

                        """,
                    #5.供暖季度日数
                    "查询供暖季度日数":"""

                     公式：
                        HDD_season = ∑_{i=1}^{120} (T_base − T_avgᵢ)

                        T_avgᵢ = (1 / 24) × ∑_{h=0}^{23} Tᵢ,ₕ

                    公式描述：
                        采暖度日数（HDD22）是一年中当某天室外日平均温度低于22℃时，将该日平均温度与22℃的差值度数乘以1天，所得出的乘积的累加值。其单位为℃·d。供暖季度日数为供暖季内每日的度日数之和。

                    对应参数含义：
                        HDD_season ：供暖季度日数（单位：℃·季）；
                        T_base：度日数基准温度，取22℃（单位：℃）；
                        Tᵢ,ₕ：i日h小时的气温（单位：℃）；
                        T_avgᵢ：i日的平均气温（单位：℃）；
                        i取1到120因为供暖季共120日，即前一年11月15日至次年3月15日；


                    数据库所在字段：
                        T：ods_sc01_ntjt_zhgr_heat_weather_info_log表temp；
                        i、h：ods_sc01_ntjt_zhgr_heat_weather_info_log表的data_time字段，格式为：YYYY-MM-DD HH:MM:SS，其中年月日为i日，小时为h，该表的temp为每小时一条数据；
			
                    """,
                    #6 换热站采暖季度日数热单耗
                    "换热站采暖季度日数单耗":"""

                        度日数单耗计算公式：   
                            qₐ_hdd = qₐ / HDD_select
                            qₐ = [(Qₐ(t=end) - Qₐ(t=start)) / Aₐ] × (24 × 120) / (t=end - t=start)
                            HDD_select = ∑_{i=D_start}^{D_end} (T_base − T_avgᵢ)
                            T_avgᵢ = (1 / 24) × ∑_{h=0}^{23} Tᵢ,ₕ        

                        如何拆解子问题：
                            在子问题拆解时，
                            1、先求出换热站指定时间段内的热单耗
                            2、求换热站指定时间段内的度日数
                            
                        度日数单耗公式解释：
                            度日数热单耗是指在单位度日数（如 1℃・天）下，建筑或系统单位面积的平均耗热量，用于衡量建筑的供暖能耗效率。
                            将供暖能耗与气候条件（度日数）关联，消除气候差异对能耗对比的影响，便于不同地区、不同建筑的节能性能评估。
                            换热站a指定时段度日数单耗 = 换热站a指定时段内单位面积热单耗 / 指定时段度日数
                            指定时段度日数 = 从起始日到结束日，每日度日数基准温度-每日的平均温度，所有日期的累加之和
                            每日的平均温度 = 一天24小时的气温的平均值。
                     
                        对应字段解释：
                            qₐ_hdd：换热站a指定时段度日数单耗；
                            qₐ：换热站a指定时段内单位面积热单耗（单位： GJ/m²·季）；
                            Qₐ(t=end)：换热站a指定时段结束时间的一次侧累计热量（单位：GJ）；
                            Qₐ(t=start)：换热站a指定时段起始时间的一次侧累计热量（单位：GJ）；
                            Aₐ：换热站a供热面积（单位：m²）；
                            (t=end - t=start)：指定时段时间长度（单位：小时H）；
                            t：时间；
                            HDD_select ：指定时段度日数（单位：℃·天）；
                            T_base：度日数基准温度，取22℃（单位：℃）；
                            Tᵢ,ₕ：i日h小时的气温（单位：℃）；
                            T_avgᵢ：i日的平均气温（单位：℃）；
                            D_start：计算指定时段度日数的起始日；
                            D_end：计算指定时段度日数的结束日；

                    公式中的参数在数据库对应的字段：
                        Qₐ：ods_sc01_ntjt_zhgr_heat_station_inst_data表stn_id为a的stn_prim_total_hheat；
                        Aₐ：ods_sc01_ntjt_zhgr_heat_station_info表stn_id为a的heat_area；
                        t：ods_sc01_ntjt_zhgr_heat_station_inst_data表data_time；
                        T：ods_sc01_ntjt_zhgr_heat_weather_info_log表temp；
                        i、h：ods_sc01_ntjt_zhgr_heat_weather_info_log表的data_time字段，格式为：YYYY-MM-DD HH:MM:SS，其中年月日为i日，小时为h，该表的temp为每小时一条数据；

                                        """,
                    #7 热源厂热泵指定时段COP
                    "热源厂热泵指定时段COP":"""

                        公式： 
                        COPₐ = (Q_circₐ(t=end) - Q_circₐ(t=start)) / 
                        [ (Q_intₐ(t=end) - Q_intₐ(t=start)) + (Vₐ(t=end) - Vₐ(t=start)) × H × 0.00000418585 ]
                    
                    公式描述：
                        输出热量与输入驱动热量的比值，反映了热能驱动下的能效水平。
                        
                    参数含义：
                        COPₐ：热泵a在指定时段的COP（%）；
                        t=start：指定时段的开始时间；
                        t=end：指定时段的结束时间；
                        Q_circₐ：热泵a的循环水累计热量（单位：GJ）；
                        Q_intₐ：热泵a的中介水累计热量（单位：GJ）；
                        Vₐ：热泵a的燃气累计耗气量（单位：m³）；
                        H：燃气单位体积热值（单位：kcal/m³）；
                        0.00000418585：热值单位换算系数（kcal → GJ）；
                        t：时间；

                    数据库对应字段：
                        Q_circₐ：ods_sc01_ntjt_zhgr_heat_heatpump_inst_data表中pump_id为a的circulate_water_total_hheat；
                        Q_intₐ：ods_sc01_ntjt_zhgr_heat_heatpump_inst_data表中pump_id为a的intermediary_water_total_hheat；
                        Vₐ：ods_sc01_ntjt_zhgr_heat_heatpump_inst_data表中pump_id为a的heatpump_total_gas；
                        t：ods_sc01_ntjt_zhgr_heat_heatpump_inst_data表data_time；
			            H：ods_sc01_ntjt_zhgr_heat_calorific_info表中delivery_time最新的calorific_value；      
                                      
                    """,
                    # 8 热源厂锅炉指定时段热效率
                    "热源厂锅炉指定时段热效率":"""

                    公式：eₐ = (Qₐ(t=end) - Qₐ(t=start)) / ((Vₐ(t=end) - Vₐ(t=start)) × H × 0.00000418585)
                    
                    公式中参数含义：
                        eₐ：锅炉a在指定时段的热效率（单位：无量纲，乘以 100 表示百分比 %）；
                        Qₐ(t=end)：锅炉a在指定时段结束时间的累计热量（单位：GJ）；
                        Qₐ(t=start)：锅炉a在指定时段起始时间的累计热量（单位：GJ）；
                        Vₐ(t=end)：锅炉a在指定时段结束时间的燃气累计用量（单位：m³）；
                        Vₐ(t=start)：锅炉a在指定时段起始时间的燃气累计用量（单位：m³）；
                        H：燃气单位体积热值（单位：kcal/m³）；
                        0.00000418585：热值单位换算系数（kcal → GJ）；
                        t：时间；
                        
                    公式中的参数在数据库对应的字段：
                        Qₐ：ods_sc01_ntjt_zhgr_heat_boiler_inst_data表blr_id为a的blr_total_heat；
                        Vₐ：ods_sc01_ntjt_zhgr_heat_boiler_inst_data表blr_id为a的blr_gas_total_hflow；
                        H：ods_sc01_ntjt_zhgr_heat_calorific_info表中delivery_time最新的calorific_value；
                        t：ods_sc01_ntjt_zhgr_heat_boiler_inst_data表的data_time；
                                       """,

                    #9 热源厂锅炉指定时段负荷率
                    "热源厂锅炉指定时段负荷率":"""

                        公式：LRₐ = (Qₐ(t=end) - Qₐ(t=start)) / (42 × 3600 × 0.001 × ((t=end - t=start) + 1) × 100%

                        公式描述：
                            锅炉负荷率是指锅炉在实际运行过程中输出的热功率（或供热量）与设计额定热功率（或额定供热量）的比值.它反映了锅炉实际运行负荷与设计能力的匹配程度，是评估锅炉运行效率、能耗水平及经济性的关键指标。

                            负荷率= 实际供热量 / 额定功率 * 3600*小时数 * 100%


                        对应字段解释：
                            LRₐ：锅炉id为a的锅炉负荷率（Load Ratio，百分比）；
                            Qₐ：锅炉id为a的锅炉累计热量（单位：GJ）；
                            (t=end - t=start)：指定时段的小时数（单位：H）；
                            42：锅炉额定热功率为42MW，则锅炉额定供热量为额定热功率 × 运行时间，如额定功率 2.8MW 的锅炉连续运行 1 小时的额定供热量为 (2.8 * 3600 = 10080 MJ = 10.08 GJ)；

                        数据库对应字段：
                            Qₐ：ods_sc01_ntjt_zhgr_heat_boiler_inst_data表blr_id为a的blr_total_heat；
                            t：ods_sc01_ntjt_zhgr_heat_boiler_inst_data表的data_time；

                        """,

                     # 10 换热站机组换热器对数平均温差
                     "换热站机组换热器对数平均温差":"""

                     公式：ΔT_lm = [(T₁ - T₄) - (T₂ - T₃)] / ln[(T₁ - T₄) / (T₂ - T₃)]

                     公式描述：
                        对数平均温差是某一时刻下换热器两侧的各参数计算所得指标，用于衡量换热效率。
                     
                     公式中参数含义：
                        ΔT_lm：机组换热器对数平均温差LMTD（单位：℃）；
                        T₁：机组换热器的一次侧进口温度（单位：℃）；
                        T₂：机组换热器的一次侧出口温度（单位：℃）；
                        T₃：机组换热器的二次侧进口温度（单位：℃）；
                        T₄：机组换热器的二次侧出口温度（单位：℃）；
                        
                    公式中的参数在数据库对应的字段：
                        T₁：ods_sc01_ntjt_zhgr_heat_station_inst_data表stn_prim_sup_temp
                        T₂：ods_sc01_ntjt_zhgr_heat_station_inst_data表stn_prim_ret_temp
                        T₃：ods_sc01_ntjt_zhgr_heat_station_inst_data表stnX_seco_sup_temp，其中若是计算换热站a机组X的板换对数平均温差，则筛选stn_id为a的stnX_seco_sup_temp，机组号替换X进行字段筛选，机组1则该字段为stn1_seco_sup_temp，机组2则该字段为stn2_seco_sup_temp；
                        T₄：ods_sc01_ntjt_zhgr_heat_station_inst_data表stnX_seco_ret_temp，其中若是计算换热站a机组X的板换对数平均温差，则筛选stn_id为a的stnX_seco_ret_temp，机组号替换X进行字段筛选，机组1则该字段为stn1_seco_ret_temp，机组2则该字段为stn2_seco_ret_temp；
                        t：ods_sc01_ntjt_zhgr_heat_station_inst_data表data_time；
                     """,

                    #11 换热站入住率
                    "计算换热站的入住率": """

                    计算公式：ORₐ = A_actualₐ / A_meshₐ × 100%
                   
                   公式描述：
                      换热站入住率是指换热站所服务的供热区域内，实际入住并使用供热的用户供暖面积占设计规划的全部用户的入网面积的比例。它是衡量供热系统实际负荷与设计负荷匹配程度的重要指标，常用于评估供热效率、能耗水平及管网运行状态。入住率（建筑面积）= 实际供热的建筑面积 / 设计总建筑面积 ×100%
                      
                   公式中参数含义：
                        ORₐ：换热站id为a的换热站入住率（Occupancy Rate，100%）
                        A_actualₐ：换热站id为a的换热站实际供热建筑面积，已开通供热的房屋建筑面积之和（单位：㎡）；
                        A_meshₐ：换热站id为a的换热站设计总建筑面积（单位：㎡）；

                    字段在数据库中对应字段信息：
                        A_actualₐ：ods_sc01_ntjt_zhgr_heat_station_info表stn_id为a的heat_area；
                        A_meshₐ：ods_sc01_ntjt_zhgr_heat_station_info表stn_id为a的mesh_area；
                   
                   """,
                   #12 热网指定时段热量损失率
                   "热网指定时段热量损失率":"""

                        公式：NL = ((Q_source(t=end) - Q_source(t=start)) - (∑(Q_station_i(t=end) - Q_station_i(t=start)))) / (Q_source(t=end) - Q_source(t=start)) × 100%

                        公式解释：
                            供热网损率是指在供热系统中，由于管网散热、管道泄漏等原因导致的热量损失占总供热量的比例。它是衡量供热管网运行效率和节能水平的重要指标，网损率越低，说明供热系统的热量利用效率越高，能源浪费越少。

                            网损率 = (热网供热量-∑换热站用热量)/热网供热量*100%

                            热网供热量：供热系统从热源输出的总热量，单位吉焦（GJ）。
                            换热站供热量：有效供热量，最终输送到用户端并被实际利用的热量，即用户实际接收的热量。

                       公式字段解释：
                            NL：热网指定时段热量损失率（Net Loss，100%）
                            Q_source：热源厂累计热量（单位：GJ）；
                            Q_station_i：换热站id为i的换热站累计热量（单位：GJ）；
                            ∑(Q_station_i(t=end) - Q_station_i(t=start))：所有换热站的指定时段累计热量差值之和（单位：GJ），i为换热站id，需计算所有不同id的换热站的指定时段累计热量差值之和；
                            t：时间；

                        数据库对应字段信息：
                            Q_source：ods_sc01_ntjt_zhgr_heat_source_inst_data表中src_id为1的src_sup_total_hheat；
                            Q_station_i：ods_sc01_ntjt_zhgr_heat_station_inst_data表stn_id为i的stn_prim_total_hheat；
                            t：ods_sc01_ntjt_zhgr_heat_station_inst_data表data_time；

                    """,
                   #13 换热站指定时段电单耗
                    "换热站指定时段电单耗":"""

                    公式：电单耗_换热站i = (E_换热站i(t=end) - E_换热站i(t=start)) × 24 × 120 / A_换热站i / ((t=end - t=start) + 1)
                    
                    公式描述：
                        单位面积电单耗是指在供热系统运行过程中，每平方米供热面积在一定时间内消耗的电量，是衡量供热系统电能利用效率与节能水平的重要指标。电单耗越低，说明供热系统的电节能性越好。
                    
                    公式中参数含义：
                       电单耗_换热站i：换热站id为i的换热站指定时段电单耗，单位kWh/㎡·季；
                       E_换热站i：换热站id为i的累计耗电量（单位：kWh）；
                       A_换热站i：换热站id为i的供热面积（单位：㎡）;
                       t：时间；
                      (t=end - t=start)：指定时段的小时数，单位H；

                   数据库对应字段信息：
                        E_换热站i：ods_sc01_ntjt_zhgr_heat_station_inst_data表stn_id为i的stn_total_elec；
                        A_换热站i：ods_sc01_ntjt_zhgr_heat_station_info表stn_id为i的heat_area；
                      t：ods_sc01_ntjt_zhgr_heat_station_inst_data表data_time；

                            """,

                   #14 换热站指定时段水单耗
                   "换热站指定时段水单耗":"""
                   公式： A_换热站i的水单耗= (∑_{jz=1}^{n}((W_换热站i(t=end) - W_换热站i(t=start)))) × 1000 × 120 × 24 / A_换热站i / ((t=end - t=start) + 1)
                   公式描述：
                       单位面积水单耗是指在供热系统中，每平方米供热面积在一定时间内消耗的水量，用于反映循环水系统的补水率、泄漏量及运行管理水平，水单耗越低，说明系统的水资源浪费越少，管网密封性和运行效率越高。
                       注意：上面公式中， × 120：表示一个采暖季有120天。  × 24小时：表示每天有24个小时。这两个信息和公式中 “/ ((t=end - t=start) + 1)”强相关。如果除以的时间是以天为单位，例如：TIMESTAMPDIFF(DAY, s.start_time, e.end_time)中， 按照天计算。则公式中只需要× 120就可以。
                       如果除以的时间是以小时为单位，例如：(TIMESTAMPDIFF(HOUR, s.start_time, e.end_time)+1)中， 是按照小时计算。则公式中需要  × 120 × 24。
                       公式中的“× 120 × 24/((t=end - t=start) + 1)”,是将一段时间换成“季”的单位换算。

                    公式中参数含义：    
                       水单耗_换热站i：换热站id为i的换热站指定时段水单耗，单位kg/㎡·季；
                        W_换热站i：换热站id为i的机组累计耗水量（单位：m³）；
                        A_换热站i：换热站id为i的供热面积（单位：㎡）;
                        t：时间；
                        (t=end - t=start)：指定时段的小时数，单位H；
                        jz：机组数量，若机组数量大于1，则换热站i水单耗为多机组的水单耗差值之和；

                  数据库对应字段信息：
                    W_换热站i：ods_sc01_ntjt_zhgr_heat_station_inst_data表stn_id为i的stn{jz}_seco_repl_total_flow，jz为机组id，例如1、2、3，换热站机组数量存储在ods_sc01_ntjt_zhgr_heat_station_info的plan_num；其中换热站a机组X的累计耗水量，筛选stn_id为a的stnX_seco_repl_total_flow，机组号替换X进行字段筛选，机组1则该字段为stn1_seco_repl_total_flow，机组2则该字段为stn2_seco_repl_total_flow；若是plan_num只有1，那么只需要获取计算stn1_seco_repl_total_flow，若是plan_num不是1，则需要计算stn1_seco_repl_total_flow到stnX_seco_repl_total_flow的指定时间段内的耗水量，再汇总计算得到换热站的水单耗；
                    A_换热站i：ods_sc01_ntjt_zhgr_heat_station_info表stn_id为i的heat_area；
                    t：ods_sc01_ntjt_zhgr_heat_station_inst_data表data_time；

                   """,

                    #15. 锅炉指定时段单耗
                    "锅炉指定时段单耗":"""
                    公式： 锅炉a指定时段单耗 =  (Vₐ(t=end) - Vₐ(t=start)) / (Qₐ(t=end) - Qₐ(t=start))
                    
                    公式描述：
                        燃气热水锅炉热单耗是单位体积天然气燃烧后锅炉实际输出的有效热量，由天然气热值和锅炉热效率共同决定，是衡量锅炉能量利用效率和运行经济性的直接指标。
                
                    公式中参数含义：    
                        锅炉a指定时段单耗：锅炉a在指定时段的热单耗（单位：GJ/m³）；
                        Qₐ(t=end)：锅炉a在指定时段结束时间的累计热量（单位：GJ）；
                        Qₐ(t=start)：锅炉a在指定时段起始时间的累计热量（单位：GJ）；
                        Vₐ(t=end)：锅炉a在指定时段结束时间的燃气累计用量（单位：m³）；
                        Vₐ(t=start)：锅炉a在指定时段起始时间的燃气累计用量（单位：m³）；
                        t：时间；
                    
                    公式中的参数在数据库对应的字段：
                        Qₐ：ods_sc01_ntjt_zhgr_heat_boiler_inst_data表blr_id为a的blr_total_heat；
                        Vₐ：ods_sc01_ntjt_zhgr_heat_boiler_inst_data表blr_id为a的blr_gas_total_hflow；
                        t：ods_sc01_ntjt_zhgr_heat_boiler_inst_data表的data_time；
                    
	"""
    }

    with open('config/formula_descriptions.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def create_common_expressions():
    """创建常用表达配置文件"""
    data = [
        "商河地暖表示含义为：商河供热系统中所有换热站中供暖方式为地暖的",
    "商河换热站表示含义为：商河供热系统中所有换热站",
    "设计供热能力表示含义为：锅炉或热泵的额定供热能力",
    "弘德站表示含义为：换热站名称（stn_name）为弘德站的站点",
     "'供热量'、'用热量'、'用电量'、'补水量'等表述含义：用给定时间段结束时刻的值减去给定时间段开始时刻的值求差。",
     "2025年1月1日作为单独时间段出现时的表述含义为：2025年1月1日00:00:00到23:59:59的时间段",
     "2024-2025采暖季表示的含义为：2024年11月15号00:00:00到2025年3月15号00:00:00",
     "供暖季时间为前一年11月15日00:00:00至第二年03月15日00:00:00",
     "商河热源表示：商河恒泰热源厂和玉泉生物质电厂",
     "商河热源厂表示：商河恒泰热源厂",
    "用户问具体时间点信息时，默认取该时间点后第一条数据。例如2025年3月7日23点33分表示：查找2025年3月7日23点33分后的第一个值。所有时间点名词解释，一定要明确解释出该含义。",
   "商河恒泰热源厂的总燃气用量表示的含义为： 4台锅炉和2台热泵的燃气用量的总和"
    ]

    with open('config/common_expressions.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def create_table_descriptions():
    """创建数据表描述配置文件"""
    data = [
        {

        "name": "ods_sc01_ntjt_zhgr_heat_station_inst_data",
        "describe": "换热站实时数据表。主键为stn_id。",
        "detail": """
        下面内容为：列名、数据类型、列描述、示例值、正常范围最小值（如有）、正常范围最大值（如有）
        stn_id int 站点ID 2012
        data_time datetime 数据时间 2024-11-01 00:00:04
        data_id bigint 数据ID自增 1199882231
        data_storage_time datetime 加载数据的时间 2024-11-01 00:00:44
        stn_prim_sup_temp decimal 一次网供水温度 50.0200 30 100
        stn_prim_ret_temp decimal 一次网回水温度 39.5700 20 90
        stn_prim_sup_bdirt_press decimal 一次网供水污前压力 0.3891 0.01 1
        stn_prim_sup_adirt_press decimal 一次网供水污后压力
        stn_prim_ret_press decimal 一次网回水压力 0.3880 0.01 1
        stn_prim_sup_htemp decimal 一次网热表供水温度 20.0200 30 100
        stn_prim_ret_htemp decimal 一次网热表回水温度 19.5700 20 90
        stn_prim_inst_hflow decimal 一次网热表瞬时流量 0.0000 1 500
        stn_prim_total_hflow decimal 一次网热表累计流量 1032588.0000
        stn_prim_inst_hheat decimal 一次网热表瞬时热量 0.0000 1 50
        stn_prim_total_hheat decimal 一次网热表累计热量 159746.4531
        stn_eney_sup_temp decimal 新能源供水温度 
        stn_eney_ret_temp decimal 新能源回水温度 
        stn_eney_sup_bdirt_press decimal 新能源供水污前压力 0.0033
        stn_eney_sup_adirt_press decimal 新能源供水污后压力 0.0132
        stn_eney_ret_press decimal 新能源回水压力 0.0000
        stn_eney_sup_htemp decimal 新能源热表供水温度 21.3200
        stn_eney_ret_htemp decimal 新能源热表回水温度 21.0800
        stn_eney_inst_hflow decimal 新能源热表瞬时流量 0.0000
        stn_eney_total_hflow decimal 新能源热表累计流量 601263.3125
        stn_eney_inst_hheat decimal 新能源热表瞬时热量 0.0000
        stn_eney_total_hheat decimal 新能源热表累计热量 45252.4883
        stn_inst_elec decimal 瞬时用电功率 129987.6016
        stn_total_elec decimal 累计用电电度 129987.6016
        plant1_id bigint 机组1ID 201201
        stn1_set_elec_valve_open decimal 电动调节阀给定开度1 71.3000 0 100
        stn1_inst_elec_valve_open decimal 电动调节阀实际开度1 71.3537 0 100
        stn1_seco_sup_temp decimal 二次网供水温度1 40.8000 30 80
        stn1_seco_ret_temp decimal 二次网回水温度1 30.9000 20 70
        stn1_seco_sup_press decimal 二次网供水压力1 0.3972 0.01 1
        stn1_seco_ret_bdirt_press decimal 二次网回水污前压力1 0.3543 0.01 1
        stn1_seco_ret_adirt_press decimal 二次网回水污后压力1 
        stn1_seco_sup_htemp decimal 二次网热表供水温度1 49.6000 30 80
        stn1_seco_ret_htemp decimal 二次网热表回水温度1 39.8800 20 70
        stn1_seco_inst_hflow decimal 二次网热表瞬时流量1 351.3170 1 500
        stn1_seco_total_hflow decimal 二次网热表累计流量1 1489721.0000
        stn1_seco_inst_hheat decimal 二次网热表瞬时热量1 0.2520 1 50
        stn1_seco_total_hheat decimal 二次网热表累计热量1 28709.3711
        stn1_seco_repl_inst_flow decimal 补水瞬时流量1 0.0000
        stn1_seco_repl_total_flow decimal 补水累计流量1 17888.0000
        plant2_id bigint 机组2ID 
        stn2_set_elec_valve_open decimal 电动调节阀给定开度2 0 100
        stn2_inst_elec_valve_open decimal 电动调节阀实际开度2 0 100
        stn2_seco_sup_temp decimal 二次网供水温度2 30 80
        stn2_seco_ret_temp decimal 二次网回水温度2 20 70
        stn2_seco_sup_press decimal 二次网供水压力2 0.01 1
        stn2_seco_ret_bdirt_press decimal 二次网回水污前压力2 0.01 1
        stn2_seco_ret_adirt_press decimal 二次网回水污后压力2 
        stn2_seco_sup_htemp decimal 二次网热表供水温度2 30 80
        stn2_seco_ret_htemp decimal 二次网热表回水温度2 20 70
        stn2_seco_inst_hflow decimal 二次网热表瞬时流量2 1 500
        stn2_seco_total_hflow decimal 二次网热表累计流量2 
        stn2_seco_inst_hheat decimal 二次网热表瞬时热量2 1 50
        stn2_seco_total_hheat decimal 二次网热表累计热量2 
        stn2_seco_repl_inst_flow decimal 补水瞬时流量2 
        stn2_seco_repl_total_flow decimal 补水累计流量2 
        plant3_id bigint 机组3ID 
        stn3_set_elec_valve_open decimal 电动调节阀给定开度3 0 100
        stn3_inst_elec_valve_open decimal 电动调节阀实际开度3 0 100
        stn3_seco_sup_temp decimal 二次网供水温度3 30 80
        stn3_seco_ret_temp decimal 二次网回水温度3 20 70
        stn3_seco_sup_press decimal 二次网供水压力3 0.01 1
        stn3_seco_ret_bdirt_press decimal 二次网回水污前压力3 0.01 1
        stn3_seco_ret_adirt_press decimal 二次网回水污后压力3 
        stn3_seco_sup_htemp decimal 二次网热表供水温度3 30 80
        stn3_seco_ret_htemp decimal 二次网热表回水温度3 20 70
        stn3_seco_inst_hflow decimal 二次网热表瞬时流量3 1 500
        stn3_seco_total_hflow decimal 二次网热表累计流量3 
        stn3_seco_inst_hheat decimal 二次网热表瞬时热量3 1 50
        stn3_seco_total_hheat decimal 二次网热表累计热量3 
        stn3_seco_repl_inst_flow decimal 补水瞬时流量3 
        stn3_seco_repl_total_flow decimal 补水累计流量3 
 """
    },#heat_station_inst_data,换热站实时数据表
    {
        "name": "ods_sc01_ntjt_zhgr_heat_station_info",
        "describe": "换热站业务信息表。主键为id。heat_station_info.stn_id=heat_station_inst_data.stn_id",
        "detail": """
        下面内容为：列名、数据类型、列描述、示例值
        id integer 自增整数类型，用于唯一标识记录 2024
        stn_name character varying 换热站名称 红星天铂八地块站，换热站名称可以近似的认为是小区名称
        stn_state character 换热站状态（0：在运，1：停运，2：维修） 0
        plan_num integer 机组数量 2
        heat_method character 采暖方式 (0: 地暖 / 1: 挂暖 / 2: 中央空调 / 3: 挂暖 + 中央空调) 0
        build_type character 站点性质 (0: 居民 / 1: 公建 / 2: 医院 / 3: 学校 / 4: 工业) 0
        site_type character 站点类型（0：监控站，1：人工站，2：自管站） 0
        heat_area numeric 供热面积（默认） 41330.80
        state_time timestamp without time zone 状态变更时间
        build_time timestamp without time zone 建设时间 83324.80
        mesh_area numeric 入网面积 (建筑面积)
        trans_area numeric 传热面积
        actual_area numeric 实际供暖面积
        belong_unit character varying 所属单位 商河恒泰供热公司
        longitude numeric 经度 117.151121
        latitude numeric 纬度 37.293410
        charge_person character varying 负责人 燕景浩
        contact_info character varying 联系人 15624072319
        site_addr character varying 热站地址
        create_by character varying
        create_time timestamp without time zone 2024-10-14 21:57:17.029802
        update_by character varying
        update_time timestamp without time zone
        is_delete character 0：未删除 1：已删除 0
        remark character varying
        distance numeric 距离（拓扑距离）真实管网距离
        stn_id integer 实时表中对应的换热站 id 2024
        heatstation_code character varying ERP 中换热站唯一编码 H2023252
        source_num integer 热源数量 1
        valve_num integer 阀门数量 2
        source_type character 热源形式：(0: 地热井 / 风冷螺杆机 / 1: 空气源热泵 / 2: 燃气锅炉 / 3: 燃空气源热泵 / 4: 水网 / 5: 基汽 / 6: 综合能源) 4
        energy_save_type character 节能类型：(0: 非节能 / 1: 一步节能 / 2: 二步节能 / 3: 三步节能 / 4: 四步节能) 4
        serial_num integer 站点排序
    """
    },#heat_station_info,换热站信息表。静态表

       {
        "name": "ods_sc01_ntjt_zhgr_heat_source_inst_data",
        "describe": "热源实时数据表。",
        "detail": """
        下面内容为：列名、数据类型、列描述、示例值、正常范围最小值（如有）、正常范围最大值（如有）
        src_id	int	热源ID 2
        data_time	datetime	采集时间  2025-01-01 00:00:50
        data_id	bigint	数据ID自增  86
        data_storage_time	datetime	落库时间
        src_repl_inst_flow	decimal	瞬时用水量
        src_repl_total_flow	decimal	累计用水量
        src_inst_elec	decimal	瞬时电功率
        src_total_elec	decimal	累计用电量
        src_run_load	decimal	运行负荷
        src_sup_temp	decimal	供水温度  54 40 120
        src_sup_press	decimal	供水压力  1 0.01 1
        src_sup_sup_htemp	decimal	供水热表供温  54 40 120
        src_sup_ret_htemp	decimal	供水热表回温 30 100
        src_sup_inst_hflow	decimal	热表供水瞬时流量  2779 1 3500
        src_sup_total_hflow	decimal	热表供水累计流量  2481597
        src_sup_inst_hheat	decimal	热表供水瞬时热量  162 1 600
        src_sup_total_hheat	decimal	热表供水累计热量  714622
        src_ret_temp	decimal	回水温度  38 30 100
        src_ret_press	decimal	回水压力  0 0.01 1
        src_ret_sup_htemp	decimal	回水热表供温  
        src_ret_ret_htemp	decimal	回水热表回温  39
        src_ret_inst_hflow	decimal	回水瞬时流量  2779
        src_ret_total_hflow	decimal	回水累计流量  2377179
        src_ret_inst_hheat	decimal	回水瞬时热量  181
        src_ret_total_hheat	decimal	回水累计热量  731239
        src_ret_set_elec_valve_open	decimal	回水阀门设定开度
        src_ret_inst_elec_valve_open	decimal	回水阀门实际开度
        """

    },#heat_source_inst_data,热源ID

      {
        "name": "ods_sc01_ntjt_zhgr_heat_weather_info_log",
        "describe": "商河县历史天气数据表。包含商河地区每日每小时的天气情况。",
        "detail": """
        下面内容为：列名、数据类型、列描述、示例值
        data_time                 datetime  时间                                   2024-11-17 00:00:00  
        data_id                   bigint   数据ID自增                              40641  
        temp                      decimal  气温                                    18.40  
        solar                     decimal  太阳辐射                                120  
        longitude                 decimal  经度                                    117.200000  
        latitude                  decimal  纬度                                    37.330000.00  
        altitude                  decimal  海拔                                    50  
        rh                        decimal  相对湿度                                62.40 
        wind_dir                  decimal  风向                                    171.10  
        wind_speed                decimal  风速                                    2.30  
        air_pressure              decimal  气压                                    1015.00  
        rain                      decimal  降水量(mm)                              2.00  
        cloudiness_all            decimal  总云量(%)                               60.00  
        cloudiness_low            decimal  低云量(%)                               30.00 
        weather_code              int      "气天气现象(代码)0:晴,1:多云,2:阴,7:小雨  0  
        weather_desc              varchar  "天气现象(描述)0:晴,1:多云,2:阴,7:小雨    晴  
        rh_max                    decimal  最大相对湿度(%)                         75.00
        rh_min                    decimal  最小相对湿度(%)                         60.00
        """
    },
    {
        "name": "ods_sc01_ntjt_zhgr_heat_source_info",
        "describe": "供热热源厂信息表。信息为商河热源厂的相关信息。",
        "detail": """
        下面内容为：列名、数据类型、列描述、示例值
        id                 int          数据主键ID自增                                                  1  
        src_name           varchar      热源名称                                                       商河恒泰热源厂  
        src_id             int          实时数据表中的热源ID                                            1  
        src_type           bpchar       热源类型(0：燃煤锅炉1：燃气锅炉2：电锅炉3：热电联产4：能源站)      0  
        src_state          bpchar       热源状态(0：在运，1：停运，2：维修)                              0  
        state_time         timestamp    状态变更时间                                                   2024-10-08 17:34:23
        build_time         timestamp    建设时间                                                       2024-09-26 00:00:00
        heat_area          numeric      供热面积                                                       3300000.00
        mesh_area          numeric      入网面积                                                       3300000.00     
        design_heat        numeric      设计供热能力                                                   41.00
        actual_heat        numeric      实际供热能力                                                   189.00
        heat_price         numeric      热单价                                                         28.50
        belong_unit        varchar      所属单位                                                       济南市商河恒泰供热有限公司
        charge_person      varchar      负责人                                                         董作军
        contact_info       varchar      联系人电话                                                     NULL
        site_addr          varchar      地址                                                          NULL
        create_by          varchar      信息创建人                                                     NULL
        create_time        timestamp    信息创建时间                                                   2024-07-31 14:39:28 
        update_by          varchar      信息更新人                                                     1
        update_time        timestamp    信息更新时间                                                   2024-10-09 16:45:56 
        is_delete          bpchar       是否删除(0：未删除, 1：已删除)                                  0
        remark             varchar      备注                                                          NULL
        longitude          numeric      经度                                                          117.138852
        latitude           numeric      纬度                                                          37.293886
        load_coefficient   numeric      负荷预测修正系数                                               1
        """
    },
    {
        "name": "ods_sc01_ntjt_zhgr_heat_heatpump_inst_data",
        "describe": "热源厂热泵实时数据表。",
        "detail": """
        下面内容为：列名、数据类型、列描述、示例值
        data_time	datetime	采集时间	2025/2/9 22:00:24
        pump_id	varchar(10)	ID	2
        data_id	bigint(20)	数据ID自增	3921074374
        data_storage_time	datetime	Time when the data is loaded	2025/2/10 10:36:29
        generator_smoke_out_temp	decimalv3(10, 4)	发生器_烟气出口温度	92.3
        generator_gas_in_temp	decimalv3(10, 4)	发生器_燃气入口压力	0
        generator_gas_in_elec_valve_open	decimalv3(10, 4)	发生器_燃气入口阀门开度	45
        solution_in_temp	decimalv3(10, 4)	溶液板换_入口温度	41.3
        solution_out_temp	decimalv3(10, 4)	溶液板换_出口温度	78
        dilute_solution_set_frequency	decimalv3(10, 4)	稀溶液泵_频率给定	30
        concentrated_solution_set_frequency	decimalv3(10, 4)	浓溶液泵_频率给定	42
        condenser_temp	decimalv3(10, 4)	冷凝器_冷凝温度	50.5
        evaporator_temp	decimalv3(10, 4)	蒸发器_蒸发温度	20.2
        refrigerant_pump_set_frequency	decimalv3(10, 4)	冷剂泵_频率给定	38.9
        heat_network_in_temp	decimalv3(10, 4)	热网水入口温度	36.8
        heat_network_in_press	decimalv3(10, 4)	热网水入口压力	0.3999
        heat_network_out_temp	decimalv3(10, 4)	热网水出口温度	48
        heat_network_out_press	decimalv3(10, 4)	热网水出口压力	0.4663
        spray_water_out_temp	decimalv3(10, 4)	喷淋水出口温度	40.1
        spray_water_out_press	decimalv3(10, 4)	喷淋水出口压力	0.05
        circulate_water_sup_htemp	decimalv3(10, 4)	循环水热表_供水温度	45.92
        circulate_water_ret_htemp	decimalv3(10, 4)	循环水热表_回水温度	35.36
        circulate_water_inst_hflow	decimalv3(10, 4)	循环水热表_瞬时流量	407.2
        circulate_water_inst_hheat	decimalv3(10, 4)	循环水热表_瞬时热量	17.7182
        circulate_water_total_hflow	decimalv3(12, 4)	循环水热表_累计流量	942597.125
        circulate_water_total_hheat	decimalv3(12, 4)	循环水热表_累计热量	15903.1416
        intermediary_water_sup_htemp	decimalv3(10, 4)	中介水热表_供水温度	36.8
        intermediary_water_ret_htemp	decimalv3(10, 4)	中介水热表_回水温度	29.5
        intermediary_water_inst_hflow	decimalv3(10, 4)	中介水热表_瞬时流量	0
        intermediary_water_inst_hheat	decimalv3(10, 4)	中介水热表_瞬时热量	0
        intermediary_water_total_hflow	decimalv3(12, 4)	中介水热表_累计流量	102646
        intermediary_water_total_hheat	decimalv3(12, 4)	中介水热表_累计热量	3001
        heatpump_total_gas	decimalv3(10, 2)	热泵耗气量	918179.94
        oil_choke_pressure	decimalv3(10, 2)	阻油器压力	0
        heatpump_inst_gas	decimalv3(10, 2)	热泵耗气量瞬时流量	278.18
        """
    },
    {
        "name": "ods_sc01_ntjt_zhgr_heat_boiler_inst_data",
        "describe": "热源厂锅炉实时数据表。",
        "detail": """
        下面内容为：列名、数据类型、列描述、示例值
        data_time	datetime	采集时间	2024/9/23 22:06:37
        blr_id	varchar(10)	锅炉ID	2
        data_id	bigint(20)	数据ID自增	5194332224
        data_storage_time	datetime	Time when the data is loaded	2024/12/3 16:58:55
        blr_sup_temp	decimalv3(10, 4)	锅炉_供水温度	23.7
        blr_sup_press	decimalv3(10, 4)	锅炉_供水压力	0.3424
        blr_ret_temp	decimalv3(10, 4)	锅炉_回水温度	25.1
        blr_ret_press	decimalv3(10, 4)	锅炉_回水压力	0.3469
        blr_inst_flow	decimalv3(10, 4)	锅炉_供水瞬时流量	0
        blr_total_hflow	decimalv3(12, 4)	锅炉_供水累计流量	461961.0938
        blr_inst_heat	decimalv3(10, 4)	锅炉_供水热表瞬热	0
        blr_total_heat	decimalv3(12, 4)	锅炉_供水热表累热	30951.9297
        blr_gas_inst_flow	decimalv3(12, 4)	锅炉_燃气瞬时流量	0
        blr_gas_total_hflow	decimalv3(12, 4)	锅炉_燃气累计流量	0
        blr_pump_out_smoke_temp	decimalv3(10, 4)	锅炉_省煤气出口_热泵入口烟温	23
        blr_pump_out_smoke_press	decimalv3(12, 4)	锅炉_省煤气出口_热泵入口烟压	0.0215
        blr_out_smoke_temp	decimalv3(10, 4)	锅炉_锅炉出口_省煤器入口_烟温	163.3102
        blr_out_smoke_press	decimalv3(10, 4)	锅炉_锅炉出口_省煤气入口_烟压	0.0331
        blr_fan_out_smoke_temp	decimalv3(10, 4)	锅炉_风机_出口烟温	17.3
        blr_fan_out_smoke_press	decimalv3(10, 4)	锅炉_风机_出口风压	0.076
        blr_fan_gas_press	decimalv3(10, 4)	锅炉_风机_燃气压力	0
        blr_fan_elec	decimalv3(10, 4)	锅炉_风机_电流	0
        blr_front_container_temp	decimalv3(10, 4)	锅炉_前上集装箱温度	23.6
        blr_back_container_temp	decimalv3(10, 4)	锅炉_后上集装箱温度	23.8
        blr_economizer_in_smoke_temp	decimalv3(10, 4)	锅炉_省煤器_进口烟温	0
        blr_economizer_in_smoke_press	decimalv3(10, 4)	锅炉_省煤器_进口烟压	0
        blr_economizer_out_smoke_temp	decimalv3(10, 4)	锅炉_省煤器_出口烟温	23
        blr_economizer_out_smoke_press	decimalv3(10, 4)	锅炉_省煤器_出口烟压	0.0215
        blr_condenser_out_temp	decimalv3(10, 4)	锅炉_冷凝器_出水温度	23.3
        blr_so2	decimalv3(10, 4)	锅炉_环保_出口SO2	0
        blr_zkso2	decimalv3(10, 4)	锅炉_环保_出口SO2折算值	0
        """
    },
    {
        "name": "ods_sc01_ntjt_zhgr_heat_instruction_issue_detail",
        "describe": "供热调控阀门下发指令表",
        "detail": """
        下面内容为：列名、数据类型、列描述、示例值
        id	bigserial		134	
        strategy_id	int8	算法推荐策略详情ID	2749	
        strategy_version	varchar(14)		20241021184825	
        cmd_guid	varchar(30)	与SCADA进行通信的唯一标识	FK1297994880152240142102001	
        valve_id	varchar(60)	阀门ID	涌鑫花苑换热站.JZ1_DDFGD	
        valve_open_issue	numeric(10, 2)	阀门开度-下发	24.65	
        valve_is_work	bpchar(1)	阀门是否工作（0：未动作，1：已动作）		
        valve_open_issue_inst	numeric(10, 2)	阀门开度-下发后的实际开度		
        valve_open_issue_inst_time	timestamp	阀门开度-下发后的实际开度的时间		
        issue_by	int4	下发人		
        issue_time	timestamp	下发时间	2024/10/21 18:48:15	
        issue_json	varchar(500)	下发JSON	{"cmdGuid":"FK1297994880152240142102001","code":"200","msg":"校验成功"}	
        issue_result	bpchar(1)	下发结果：（0：失败，1：成功）	1	
        issue_result_time	timestamp	下发结果时间	2024/10/21 18:48:15	
        issue_result_json	varchar(500)	下发结果json		
        issue_fail_reason	varchar(500)	下发失败的原因	校验成功	
        feedback_time	timestamp	反馈时间		
        feedback_result	bpchar(1)	反馈结果：（0：失败，1：成功）	0	
        feedback_json	varchar(500)	反馈JSON		
        create_by	int4			
        create_time	timestamp		2024/10/21 18:42:48	
        update_by	int4			
        update_time	timestamp			
        remark	varchar(500)			
        stn_busi_id	int4		1020	
        plant_busi_id	int4		102001	
        send_id	int4		8	
        """
    }
]

        # 这里只添加了两个示例，你可以继续添加其他表


    with open('config/table_descriptions.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    """创建配置文件目录和文件"""
    # 创建配置目录
    if not os.path.exists('config'):
        os.makedirs('config')
        print("创建配置目录: config")

    # 创建配置文件
    create_formula_descriptions()
    print("创建公式描述文件: config/formula_descriptions.json")

    create_common_expressions()
    print("创建常用表达文件: config/common_expressions.json")

    create_table_descriptions()
    print("创建数据表描述文件: config/table_descriptions.json")

    print("\n配置文件创建完成！请检查并补充完整的数据。")


if __name__ == "__main__":
    main()