// Public tool schema from the user-authorized source. All 15 steps retained.
export const steps = [
            {
                id: 'company-info',
                title: '企业信息',
                icon: 'fa-building',
                description: '输入企业基本信息，作为后续步骤的输入',
                fields: [
                    { type: 'input', name: '企业名称', placeholder: '请输入企业名称（建议10字以内）...', maxlength: 40, isShortField: true },
                    { type: 'textarea', name: '主营业务', placeholder: '描述企业主营业务...' },
                    { type: 'textarea', name: '行业描述', placeholder: '描述所属行业、行业特点、市场规模等...' },
                    { type: 'textarea', name: '企业规模', placeholder: '描述员工规模、年营收、主要客户等...' },
                    { type: 'textarea', name: '企业现状', placeholder: '描述企业当前的发展阶段、核心优势、主要挑战等...' }
                ]
            },
            {
                id: 'gap',
                title: '差距分析',
                icon: 'fa-bullseye',
                description: '分析业绩差距与机会差距',
                fields: [
                    { type: 'table', name: '业绩差距', columns: ['关键指标类别', '指标', '现状', '目标', '差距'] },
                    { type: 'textarea', name: '机会差距', placeholder: '描述市场机会和技术能力差距。机会差距是现有经营结果和新的业务设计所能带来的经营结果之间差距的一种量化的评估。填补一个机会差距需要有新的业务设计...' }
                ]
            },
            {
                id: 'market-insight',
                title: '市场洞察',
                icon: 'fa-eye',
                description: '了解客户需求、竞争者的动向、技术的发展和市场经济状况以找到机遇和风险，解释市场上正在发生什么以及这些改变对公司来说意味着什么',
                fields: [
                    { type: 'textarea', name: '宏观分析', placeholder: '分析宏观环境（经济、政治、社会、技术创新等）对行业的影响，整体市场空间、行业整体趋势、外部环境的影响、产业链特征及变化趋势...' },
                    { type: 'textarea', name: '竞争动向', placeholder: '分析整个竞争市场上发生的变化，主要竞争对手的战略、价值主张、主要竞争策略/手段，目前的竞争格局，与主要竞争对手相比的优劣势，值得借鉴的地方（标杆分析）...' },
                    { type: 'textarea', name: '客户分析', placeholder: '分析客户细分标准、客户的战略重点、对服务业务的需求偏好及痛点、面临的压力和挑战、关键购买因素、客户需求与当务之急的挑战...' },
                    { type: 'textarea', name: '核心竞争力分析', placeholder: '分析企业的核心竞争力，包括财务资源、技术资源、市场地位/声誉、产品、人员等方面的优势和劣势...' }
                ]
            },
            {
                id: 'strategic-intent',
                title: '战略意图',
                icon: 'fa-flag',
                description: '组织机构的方向和最终目标，与公司的战略重点相一致，体现竞争优势',
                fields: [
                    { type: 'textarea', name: '愿景', placeholder: '可持续的、占优势的业务领先地位，展示长期的、可持续的获利能力。纲领意义，感情契约，现实但有挑战性...' },
                    { type: 'textarea', name: '战略目标', placeholder: '有效的、合理的、灵活的运营模式赢得现有市场的增长机会，但同时保持快速适应市场变化的能力。包括产品、服务、市场、客户、技术及时机等，3-5年后的业务特征和关键指标体系（如收入、份额、人均服务产值等）...' },
                    { type: 'textarea', name: '近期目标', placeholder: '业绩可衡量的指标，包括利润、成长率、市场份额、客户满意度及新产品等...' }
                ]
            },
            {
                id: 'innovation-focus',
                title: '创新焦点',
                icon: 'fa-lightbulb',
                description: '进行与市场同步的探索与试验，从广泛的资源中过滤想法，通过试点和深入市场的实验探索新想法，谨慎地进行投资和处理资源，以应对行业的变化',
                fields: [
                    { type: 'textarea', name: '未来业务组合', placeholder: '分析业务组合战略，明确各子业务或子产品属于H1（核心业务）、H2（成长业务）还是H3（新兴机会），以及各业务的管理重点与指标...' },
                    { type: 'table', name: '创新模式', columns: ['创新类型', '创新内容', '优先级', '资源投入'] },
                    { type: 'textarea', name: '资源利用', placeholder: '描述如何谨慎地进行投资和处理资源，以应对行业的变化，包括资源配置策略、投资优先级等...' }
                ]
            },
            {
                id: 'business-design',
                title: '业务设计',
                icon: 'fa-briefcase',
                description: '对外部的深入理解，为利用内部能力和持续增加价值探索的业务设计提供了基础。业务设计是迈向执行的关键',
                fields: [
                    { type: 'textarea', name: '客户选择', placeholder: '选择客户的标准，如何确定优先级：谁是你的客户，谁不是。在该细分市场下，客户有哪些特定的需求？快速增长市场...' },
                    { type: 'textarea', name: '价值主张', placeholder: '客户需求：我们提供的产品和服务是否以客户的最终需求为导向。独特性：客户是否真正认可我们的产品和服务。有影响力：是否能帮助客户实现增值和收益...' },
                    { type: 'textarea', name: '价值获取', placeholder: '如何赚钱？我们依靠什么吸引客户并获取利润？有其他的盈利模式吗？（传统的产品销售、服务协议、许可证、使用费、知识产权销售等）...' },
                    { type: 'textarea', name: '活动范围', placeholder: '经营活动中的角色和范围。哪些外包、外购？与合作伙伴的协作。公司致力于哪些业务活动？（What）如何联结公司的各业务活动？（How）如何选择最合适业务活动的地点？（Where）...' },
                    { type: 'textarea', name: '持续价值增值', placeholder: '客户需求的转移趋势。价值链中的地位。我们如何保护利润：快速响应，有效控制成本，专利等。企业如何最好地确保为客户长期提供持续的价值增值？...' },
                    { type: 'textarea', name: '风险管理', placeholder: '不确定性。潜在风险：市场、对手、技术。全面视角：外部、内部。如何保证对造就成败的不确定因素的识别、理解与管理？背后的根本原因是否被理解？...' }
                ]
            },
            {
                id: 'key-tasks',
                title: '关键任务',
                icon: 'fa-tasks',
                description: '满足业务设计和它的价值主张的要求所必须的行动。支持业务设计、尤其是价值主张的实现，主要是指持续性的战略举措，包括业务增长举措和能力建设举措',
                fields: [
                    { type: 'table', name: '关键任务', columns: ['关键任务领域', '任务名称', '负责人', '时间节点', '依赖关系'] },
                    { type: 'textarea', name: '相互依赖关系', placeholder: '描述关键任务之间的相互依赖关系，包括内部的互相依赖关系、供应商（与交易相关的同盟者）、外包合作伙伴、顾客与渠道、兴趣社区/团体、影响者等。考虑信任、同盟、灵活性、权责、澄清等方面...' }
                ]
            },
            {
                id: 'customer-channel',
                title: '客户成长',
                icon: 'fa-user-friends',
                description: '设计洞察体系、体验方案、价值模型',
                fields: [
                    { type: 'textarea', name: '客户洞察', placeholder: '描述客户数据收集与分析体系...' },
                    { type: 'textarea', name: '客户体验', placeholder: '描述客户旅程设计和体验优化方案...' },
                    { type: 'textarea', name: '客户价值', placeholder: '描述客户价值模型和价值提升策略...' }
                ]
            },
            {
                id: 'organization-channel',
                title: '组织文化',
                icon: 'fa-users',
                description: '根据关键任务和业务设计的要求，构建组织能力以支撑战略目标和期望的业务设计的实现',
                fields: [
                    { type: 'textarea', name: '正式组织', placeholder: '为确保关键任务和流程能有效地执行，需建立相应的组织结构、管理和考核标准，包括：组织架构、管理体系和流程；资源和权力如何在组织中分配（授权、行权与问责、决策流程、协作机制、信息和知识管理）；关键岗位的设置和能力要求；管理和考核标准（管理幅度和管理跨度、管理与考评、奖励与激励系统、职业规划、人员和活动的物理位置）...' },
                    { type: 'textarea', name: '人才', placeholder: '关键岗位和人才布局有什么要求（人才需求详细定义）。人才和能力的差距及挑战（欠缺哪些能力）。获得：内部获取，及时培养，外部获取。激励与保留。人力资源的特点、能力以及竞争力，使员工有能力、动力和行动来实施关键任务...' },
                    { type: 'textarea', name: '氛围与文化', placeholder: '创造好的工作环境以激励员工完成关键任务。文化：价值、信念、态度、行为、个人、团队、成功、失败、社会管制系统、规范。组织氛围：对工作环境的感知。文化变革的杠杆：参与、责任、领导者行为、信息支持、奖励等...' }
                ]
            },
            {
                id: 'ea-channel',
                title: '企业架构',
                icon: 'fa-server',
                description: '设计技术架构、治理机制、演进路线',
                fields: [
                    { type: 'textarea', name: '架构设计', placeholder: '描述技术架构蓝图...' },
                    { type: 'textarea', name: '架构治理', placeholder: '描述治理组织、流程、标准...' },
                    { type: 'textarea', name: '架构演进', placeholder: '描述演进路线图和成熟度评估...' }
                ]
            },
            {
                id: 'finance-channel',
                title: '财务投资',
                icon: 'fa-dollar-sign',
                description: '设计预算计划、控制机制、绩效指标',
                fields: [
                    { type: 'table', name: '财务规划', columns: ['年度', '总投资', '技术投资', '人才投资', '市场投资'] },
                    { type: 'textarea', name: '财务控制', placeholder: '描述成本控制、预算管理、财务合规机制...' },
                    { type: 'table', name: '财务绩效', columns: ['指标', '第1年目标', '第2年目标', '第3年目标'] }
                ]
            },
            {
                id: 'leadership',
                title: '领导力',
                icon: 'fa-user-tie',
                description: '领导力是根本。BLM业务领先模型是创造快速和持续适应不断改变的业务的核心，它的运用是公司的高层管理者需要具备的基本能力和必备能力',
                fields: [
                    { type: 'textarea', name: '领导力素质', placeholder: '领导是否展示出了风格上的多样性？领导是否起到了达到结果所需的行为示范作用？提供清楚的方向、树立高的期望值、减少官僚作风、让个人和集体为他们的行为负责、指导个人达到良好的表现...' },
                    { type: 'textarea', name: '领导力风格', placeholder: '领导是否培育了一种激励人心的氛围？领导在推动战略和执行上的角色。领导力的角色：70%的战略与执行，28%的氛围与文化...' }
                ]
            },
            {
                id: 'values',
                title: '价值观',
                icon: 'fa-heart',
                description: '价值观是基础。价值观是我们决策与行动的基本准则',
                fields: [
                    { type: 'textarea', name: '核心价值观', placeholder: '描述核心价值观（如：成就客户，创新为要，诚信负责）。作为业务的主要战略家的总经理，要确保价值观反映在公司的战略上。各级领导者要确保价值观是日常执行中的一部分...' },
                    { type: 'textarea', name: '价值观落地', placeholder: '描述价值观如何落地到战略和执行中，如何确保价值观是日常执行中的一部分...' }
                ]
            },
            {
                id: 'strategy-validation',
                title: '战略逻辑校验',
                icon: 'fa-check-circle',
                description: '检查各步骤输入输出的逻辑承接关系，评估战略规划的完整性',
                fields: [
                    { type: 'validation', name: '逻辑校验报告' }
                ]
            },
            {
                id: 'revision',
                title: '根据校验建议修改',
                icon: 'fa-edit',
                description: '根据校验报告的建议，对相应部分内容进行修改和完善',
                fields: [
                    { type: 'revision', name: '修改建议列表' }
                ]
            }
        ];
