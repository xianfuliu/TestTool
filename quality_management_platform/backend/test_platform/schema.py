from __future__ import annotations

SCHEMA_SQL = [
    """
    CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(100) NOT NULL UNIQUE,
        password_hash VARCHAR(255) NOT NULL,
        email VARCHAR(255) NOT NULL UNIQUE,
        business_line VARCHAR(255) DEFAULT '',
        is_admin BOOLEAN DEFAULT FALSE,
        last_login_at DATETIME NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS user_sessions (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        session_token VARCHAR(128) NOT NULL UNIQUE,
        expires_at DATETIME NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_user_id (user_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS email_verification_codes (
        id INT AUTO_INCREMENT PRIMARY KEY,
        email VARCHAR(255) NOT NULL,
        verification_code VARCHAR(12) NOT NULL,
        used BOOLEAN DEFAULT FALSE,
        expires_at DATETIME NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_email_code (email, verification_code)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS business_groups (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(100) NOT NULL UNIQUE,
        description TEXT,
        created_by VARCHAR(50) DEFAULT 'admin',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS projects (
        id INT AUTO_INCREMENT PRIMARY KEY,
        business_group_id INT NULL,
        name VARCHAR(100) NOT NULL,
        description TEXT,
        created_by VARCHAR(50) DEFAULT 'admin',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_business_group_id (business_group_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS api_folders (
        id INT AUTO_INCREMENT PRIMARY KEY,
        project_id INT NOT NULL,
        parent_id INT NULL,
        name VARCHAR(100) NOT NULL,
        description TEXT,
        sort_order INT DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_project_id (project_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS api_templates (
        id INT AUTO_INCREMENT PRIMARY KEY,
        project_id INT NOT NULL,
        folder_id INT NULL,
        name VARCHAR(100) NOT NULL,
        method VARCHAR(10) DEFAULT 'GET',
        url_path VARCHAR(500) DEFAULT '',
        headers JSON NULL,
        params JSON NULL,
        body JSON NULL,
        description TEXT,
        sort_order INT DEFAULT 0,
        timeout INT DEFAULT 30,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_project_id (project_id),
        INDEX idx_folder_id (folder_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS case_folders (
        id INT AUTO_INCREMENT PRIMARY KEY,
        project_id INT NOT NULL,
        parent_id INT NULL,
        name VARCHAR(100) NOT NULL,
        description TEXT,
        sort_order INT DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_project_id (project_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS test_cases (
        id INT AUTO_INCREMENT PRIMARY KEY,
        project_id INT NOT NULL,
        folder_id INT NULL,
        name VARCHAR(100) NOT NULL,
        description TEXT,
        environment_id INT NULL,
        global_vars JSON NULL,
        enable_encryption BOOLEAN DEFAULT FALSE,
        encrypt_url VARCHAR(500) DEFAULT '',
        decrypt_url VARCHAR(500) DEFAULT '',
        created_by VARCHAR(50) DEFAULT 'admin',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        sort_order INT DEFAULT 0,
        INDEX idx_project_id (project_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS test_case_steps (
        id INT AUTO_INCREMENT PRIMARY KEY,
        case_id INT NOT NULL,
        api_template_id INT NULL,
        step_order INT DEFAULT 1,
        name VARCHAR(100) DEFAULT '',
        enabled BOOLEAN DEFAULT TRUE,
        pre_processing JSON NULL,
        post_processing JSON NULL,
        assertions JSON NULL,
        variables JSON NULL,
        enable_encryption BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_case_id (case_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS environments (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        base_url VARCHAR(500) DEFAULT '',
        description TEXT,
        headers JSON NULL,
        variables JSON NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS global_tools (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        tool_type VARCHAR(50) NOT NULL,
        description TEXT,
        config JSON NULL,
        enabled BOOLEAN DEFAULT TRUE,
        created_by VARCHAR(50) DEFAULT 'admin',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS global_variables (
        id INT AUTO_INCREMENT PRIMARY KEY,
        project_id INT DEFAULT 0,
        name VARCHAR(100) NOT NULL,
        value TEXT,
        variable_type VARCHAR(30) DEFAULT 'string',
        description TEXT,
        created_by VARCHAR(50) DEFAULT 'admin',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uniq_project_var (project_id, name)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS test_schedulers (
        id INT AUTO_INCREMENT PRIMARY KEY,
        project_id INT NULL,
        name VARCHAR(100) NOT NULL UNIQUE,
        description TEXT,
        cron_expression VARCHAR(100) DEFAULT '',
        enabled BOOLEAN DEFAULT FALSE,
        case_ids JSON NULL,
        notify_emails JSON NULL,
        notify_wechat JSON NULL,
        email_config JSON NULL,
        last_run_at DATETIME NULL,
        next_run_at DATETIME NULL,
        created_by VARCHAR(50) DEFAULT 'system',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS test_reports (
        id INT AUTO_INCREMENT PRIMARY KEY,
        scheduler_id INT NULL,
        case_id INT NULL,
        project_id INT NULL,
        report_name VARCHAR(255) NOT NULL,
        status VARCHAR(50) DEFAULT 'pending',
        total_cases INT DEFAULT 0,
        passed_cases INT DEFAULT 0,
        failed_cases INT DEFAULT 0,
        error_cases INT DEFAULT 0,
        start_time DATETIME NULL,
        end_time DATETIME NULL,
        duration FLOAT DEFAULT 0,
        log_path VARCHAR(500) DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS test_step_results (
        id INT AUTO_INCREMENT PRIMARY KEY,
        report_id INT NOT NULL,
        case_id INT NULL,
        step_id INT NULL,
        step_order INT DEFAULT 1,
        status VARCHAR(50) DEFAULT 'pending',
        request_data JSON NULL,
        response_data JSON NULL,
        execution_logs TEXT,
        error_message TEXT,
        start_time DATETIME NULL,
        end_time DATETIME NULL,
        execution_time FLOAT DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_report_id (report_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS tool_card_folders (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        description TEXT,
        parent_id INT NULL,
        sort_order INT DEFAULT 0,
        is_default BOOLEAN DEFAULT FALSE,
        created_by VARCHAR(50) DEFAULT 'admin',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS tool_card_items (
        id INT AUTO_INCREMENT PRIMARY KEY,
        folder_id INT NOT NULL,
        name VARCHAR(100) NOT NULL,
        description TEXT,
        card_type VARCHAR(50) DEFAULT 'sql',
        config JSON NULL,
        mappings JSON NULL,
        sort_order INT DEFAULT 0,
        enabled BOOLEAN DEFAULT TRUE,
        created_by VARCHAR(50) DEFAULT 'admin',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_folder_id (folder_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS tool_card_sql_configs (
        id INT AUTO_INCREMENT PRIMARY KEY,
        card_id INT NOT NULL,
        host VARCHAR(255) DEFAULT '',
        port INT DEFAULT 3306,
        username VARCHAR(255) DEFAULT '',
        password VARCHAR(255) DEFAULT '',
        database_name VARCHAR(255) DEFAULT '',
        query_text LONGTEXT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uk_tool_card_sql_card_id (card_id),
        INDEX idx_tool_card_sql_card_id (card_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS tool_card_http_configs (
        id INT AUTO_INCREMENT PRIMARY KEY,
        card_id INT NOT NULL,
        url VARCHAR(1000) DEFAULT '',
        method VARCHAR(10) DEFAULT 'GET',
        headers_text LONGTEXT NULL,
        body_text LONGTEXT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uk_tool_card_http_card_id (card_id),
        INDEX idx_tool_card_http_card_id (card_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS tool_card_python_configs (
        id INT AUTO_INCREMENT PRIMARY KEY,
        card_id INT NOT NULL,
        module_name VARCHAR(255) DEFAULT '',
        class_name VARCHAR(255) DEFAULT '',
        method_name VARCHAR(255) DEFAULT '',
        args_text LONGTEXT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uk_tool_card_python_card_id (card_id),
        INDEX idx_tool_card_python_card_id (card_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS tool_card_parameters (
        id INT AUTO_INCREMENT PRIMARY KEY,
        card_id INT NOT NULL,
        field_key VARCHAR(120) NOT NULL,
        display_name VARCHAR(255) DEFAULT '',
        field_type VARCHAR(50) DEFAULT 'input',
        default_value TEXT NULL,
        required BOOLEAN DEFAULT FALSE,
        association_enabled BOOLEAN DEFAULT FALSE,
        association_field VARCHAR(120) DEFAULT '',
        association_value VARCHAR(255) DEFAULT '',
        sort_order INT DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_tool_card_param_card_id (card_id),
        INDEX idx_tool_card_param_field_key (field_key)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS tool_card_parameter_options (
        id INT AUTO_INCREMENT PRIMARY KEY,
        parameter_id INT NOT NULL,
        option_value VARCHAR(255) DEFAULT '',
        option_label VARCHAR(255) DEFAULT '',
        sort_order INT DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_tool_card_param_option_param_id (parameter_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS api_tool_products (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(120) NOT NULL UNIQUE,
        legacy_config_path VARCHAR(255) DEFAULT '',
        enable_encryption BOOLEAN DEFAULT FALSE,
        encrypt_url VARCHAR(500) DEFAULT '',
        decrypt_url VARCHAR(500) DEFAULT '',
        is_locked BOOLEAN DEFAULT FALSE,
        is_default BOOLEAN DEFAULT FALSE,
        sort_order INT DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS api_tool_schedule_tasks (
        id INT AUTO_INCREMENT PRIMARY KEY,
        product_id INT NOT NULL,
        legacy_task_id VARCHAR(120) DEFAULT '',
        job_group VARCHAR(120) DEFAULT '',
        name VARCHAR(255) NOT NULL,
        sort_order INT DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_api_tool_schedule_product_id (product_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS api_tool_layout_items (
        id INT AUTO_INCREMENT PRIMARY KEY,
        product_id INT NOT NULL,
        item_type VARCHAR(30) NOT NULL,
        item_key VARCHAR(120) DEFAULT '',
        label VARCHAR(255) DEFAULT '',
        item_name VARCHAR(255) DEFAULT '',
        data_type VARCHAR(50) DEFAULT '',
        default_value TEXT NULL,
        show_in_ui BOOLEAN DEFAULT TRUE,
        condition_field VARCHAR(120) DEFAULT '',
        formula TEXT NULL,
        formula_type VARCHAR(30) DEFAULT '',
        priority INT DEFAULT 0,
        sort_order INT DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_api_tool_layout_product_id (product_id),
        INDEX idx_api_tool_layout_item_type (item_type)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS api_tool_layout_item_options (
        id INT AUTO_INCREMENT PRIMARY KEY,
        layout_item_id INT NOT NULL,
        option_text VARCHAR(255) DEFAULT '',
        option_value VARCHAR(255) DEFAULT '',
        sort_order INT DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_api_tool_layout_option_item_id (layout_item_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS api_tool_layout_item_mappings (
        id INT AUTO_INCREMENT PRIMARY KEY,
        layout_item_id INT NOT NULL,
        mapping_key VARCHAR(255) DEFAULT '',
        mapping_value VARCHAR(255) DEFAULT '',
        sort_order INT DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_api_tool_layout_mapping_item_id (layout_item_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS api_tool_interfaces (
        id INT AUTO_INCREMENT PRIMARY KEY,
        product_id INT NOT NULL,
        name VARCHAR(255) NOT NULL,
        url VARCHAR(1000) DEFAULT '',
        method VARCHAR(10) DEFAULT 'POST',
        headers_text LONGTEXT NULL,
        request_type VARCHAR(30) DEFAULT 'normal',
        body_template_text LONGTEXT NULL,
        condition_field VARCHAR(120) DEFAULT '',
        enable_encryption BOOLEAN DEFAULT TRUE,
        timeout INT DEFAULT 30,
        sort_order INT DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uk_api_tool_product_interface (product_id, name),
        INDEX idx_api_tool_interface_product_id (product_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS api_tool_interface_condition_cases (
        id INT AUTO_INCREMENT PRIMARY KEY,
        interface_id INT NOT NULL,
        case_value VARCHAR(255) DEFAULT '',
        body_template_text LONGTEXT NULL,
        sort_order INT DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_api_tool_condition_case_interface_id (interface_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS api_tool_interface_response_mappings (
        id INT AUTO_INCREMENT PRIMARY KEY,
        interface_id INT NOT NULL,
        field_key VARCHAR(120) DEFAULT '',
        response_path VARCHAR(500) DEFAULT '',
        sort_order INT DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_api_tool_response_mapping_interface_id (interface_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS api_tool_interface_field_types (
        id INT AUTO_INCREMENT PRIMARY KEY,
        interface_id INT NOT NULL,
        field_key VARCHAR(120) DEFAULT '',
        field_type VARCHAR(50) DEFAULT '',
        sort_order INT DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_api_tool_field_type_interface_id (interface_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS api_tool_sql_configs (
        id INT AUTO_INCREMENT PRIMARY KEY,
        product_id INT NOT NULL,
        name VARCHAR(255) NOT NULL,
        host VARCHAR(255) DEFAULT '',
        port INT DEFAULT 3306,
        username VARCHAR(255) DEFAULT '',
        password VARCHAR(255) DEFAULT '',
        database_name VARCHAR(255) DEFAULT '',
        charset VARCHAR(50) DEFAULT 'utf8mb4',
        sql_text LONGTEXT NULL,
        sort_order INT DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uk_api_tool_product_sql (product_id, name),
        INDEX idx_api_tool_sql_product_id (product_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS api_tool_sql_output_fields (
        id INT AUTO_INCREMENT PRIMARY KEY,
        sql_config_id INT NOT NULL,
        field_name VARCHAR(120) DEFAULT '',
        description VARCHAR(255) DEFAULT '',
        sort_order INT DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_api_tool_sql_output_config_id (sql_config_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS system_config (
        id INT AUTO_INCREMENT PRIMARY KEY,
        config_key VARCHAR(100) NOT NULL UNIQUE,
        config_value JSON NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
]
