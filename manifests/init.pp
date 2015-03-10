class checker {

    package { ["uwsgi-plugin-python","uwsgi","nginx","python-pip", "sqlite3"]:
        ensure => latest,
    }

    service { "uwsgi":
        ensure => running,
        enable => true,
    }

    service { "nginx":
        ensure => running,
        enable => true,
    }

    file { "/etc/uwsgi/apps-enabled/checker.ini":
        ensure => file,
        source => ["puppet:///modules/checker/checker.ini"],
        require => [Package["uwsgi-plugin-python"], Package["uwsgi"]],
        notify => Service["uwsgi"],
    }

    file { "/etc/nginx/sites-enabled/checker":
        ensure => present,
        source => ["puppet:///modules/checker/nginx-checker"],
        require => Package["nginx"],
        notify => Service["nginx"],
    }

    file { "/etc/nginx/sites-enabled/default":
        ensure => absent,
        require => Package["nginx"],
        notify => Service["nginx"],
    }

    file { "/run/uwsgi":
        ensure => directory,
        owner => "www-data",
        group => "www-data",
        notify => Service["uwsgi"],
    }

    file { "/opt/checker":
        ensure => directory,
        source => ["puppet:///modules/checker/src"],
        recurse => true,
        notify => Service["uwsgi"],
    }

    exec { "pip install selenium; pip install flask; pip install requests":
        path => "/usr/bin/",
        require => Package["python-pip"],
    }

    exec { "cat /opt/checker/schema.sql | sqlite3 /tmp/checker.db || rm /tmp/checker.db":
        path => "/bin/:/usr/bin/",
        creates => "/tmp/checker.db",
        require => [Package["sqlite3"], File["/opt/checker"]],
    }

    file { "/tmp/checker.db":
        ensure => present,
        owner => "www-data",
        group => "www-data",
        require => Exec["cat /opt/checker/schema.sql | sqlite3 /tmp/checker.db || rm /tmp/checker.db"],
    }

    cron { "backup checker db":
        command => "/bin/cp /tmp/checker.db /root/checker_$(/bin/date +\\%Y-\\%m-\\%d-\\%H:\\%M).db",
        user    => root,
        hour    => 2,
        minute  => 0
    }

}
