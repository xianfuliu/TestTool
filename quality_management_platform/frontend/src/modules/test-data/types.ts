export interface TestDataConfig {
  mode: "age" | "id_number";
  min_age: number;
  max_age: number;
  age: string;
  id_number: string;
  name: string;
  gender: "random" | "male" | "female";
  ethnic_group: string;
  id_prefix: string;
  phone: string;
  bank_name: string;
  card_type: "debit" | "credit";
  bank_card: string;
  company_type: string;
  company_name: string;
  credit_code: string;
  legal_representative: string;
  address: string;
  registered_capital: string;
  establish_date: string;
  business_start_date: string;
  business_end_date: string;
  business_scope: string;
  industry_type: string;
}

export interface TestDataOptions {
  ethnic_groups: string[];
  areas: Array<{ value: string; label: string }>;
  banks: string[];
  company_types: string[];
  industries: string[];
}

export interface TestDataMeta {
  defaults: TestDataConfig;
  options: TestDataOptions;
}

export interface IdCardData {
  name: string;
  gender: string;
  ethnic_group: string;
  birth_date: string;
  birth_date_display: string;
  address: string;
  id_number: string;
  issue_authority: string;
  issue_date: string;
  expiry_date: string;
  valid_period: string;
  bank_card_number: string;
  phone_number: string;
  area_code: string;
  area_prefix: string;
  company_name: string;
  unified_social_credit_code: string;
  legal_representative: string;
}

export interface IdCardOcrData {
  front: {
    name: string;
    gender: string;
    ethnic_group: string;
    birth_date: string;
    address: string;
    id_number: string;
  };
  back: {
    issue_authority: string;
    valid_period: string;
  };
}

export interface BusinessLicenseData {
  company_name: string;
  company_type: string;
  industry_type: string;
  unified_social_credit_code: string;
  legal_person: string;
  registered_capital: string;
  establish_date: string;
  establish_date_display: string;
  business_term_start: string;
  business_term_end: string;
  business_term_display: string;
  address: string;
  business_scope: string;
}

export interface UserWorkspace {
  config: TestDataConfig;
  id_card: {
    data: IdCardData;
    ocr: IdCardOcrData;
    images: {
      front: string;
      back: string;
    };
  };
  clipboard_text: string;
  notice?: string;
}

export interface EnterpriseWorkspace {
  config: TestDataConfig;
  business_license: {
    data: BusinessLicenseData;
    image_base64: string;
  };
  clipboard_text: string;
  notice?: string;
}

export interface TestDataWorkspace {
  config: TestDataConfig;
  id_card: {
    data: IdCardData;
    ocr?: IdCardOcrData;
    images: {
      front: string;
      back: string;
    };
  };
  business_license: {
    data: BusinessLicenseData;
    image_base64: string;
  };
  clipboard_text: string;
  notice?: string;
}

export interface ResultRow {
  key: string;
  label: string;
  value: string;
  canBackfill?: boolean;
  canRefresh?: boolean;
  canCopy?: boolean;
}

export interface ResultSection {
  title: string;
  rows: ResultRow[];
}
