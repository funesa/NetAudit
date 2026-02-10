export interface Device {
    ip: string;
    hostname: string;
    mac: string;
    vendor: string;
    os_detail: string;
    device_type: string;
    status_code: 'ONLINE' | 'OFFLINE';
    last_seen: string;
    scan_type?: 'new' | 'updated';
    ports?: number[];
    services?: string[];
    printer_data?: {
        model?: string;
        status?: string;
        error_state?: string;
        console_display?: string;
        pages?: string;
        contact?: string;
        supplies?: any[];
        alerts?: string[];
        job_history?: { user: string, count: number }[];
        trays?: { name: string, capacity: number, level: number, pct: number, status: string }[];
        covers?: { name: string, status: string, is_open: boolean }[];
    };
    uptime?: string;
    location?: string;
    console_display?: string;
}

export interface ScanStatus {
    running: boolean;
    progress: number;
    total: number;
    scanned: number;
    scanned_ips: number;
    total_ips: number;
    etr: string;
    results: Device[];
    logs?: { msg: string; time: string }[];
    last_results?: {
        updated: number;
        added: number;
        total_found: number;
    };
}

export interface ADUser {
    samaccountname: string;
    name: string;
    distinguishedname: string;
    enabled: boolean;
    lastlogon: string;
    description: string;
    title: string;
    department: string;
    mail: string;
    locked?: boolean;
    groups?: string[];
}

export interface ADShare {
    server: string;
    name: string;
    path: string;
    size: string;
    free: string;
    percent: number;
    description?: string;
}

export interface FailedLogin {
    timestamp: string;
    user: string;
    source_ip: string;
    count: number;
    last_attempt: string;
}

export interface Ticket {
    id: number;
    name: string;
    status: number;
    date: string;
    content: string;
    itilcategories_id: number;
    completename?: string;
    location_name?: string;
    requester_name?: string;
    location?: string;
    locations_id?: any;
    category_name?: string;
    _users_id_recipient?: any;
}
