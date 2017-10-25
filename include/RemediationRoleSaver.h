/*
 * Copyright 2017 Red Hat Inc., Durham, North Carolina.
 * All Rights Reserved.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * Authors:
 *      Matej Tyc <matyc@redhat.com>
 */

#ifndef SCAP_WORKBENCH_REMEDIATION_ROLE_SAVER_H_
#define SCAP_WORKBENCH_REMEDIATION_ROLE_SAVER_H_

#include <QString>
#include <QFileDialog>

#include "ScanningSession.h"
#include "OscapScannerLocal.h"


/// Base for all remediation generators
template <QString* saveMessage, QString* filetypeExtension, QString* filetypeTemplate, QString* fixType>
class RemediationSaverBase
{
    public:
        RemediationSaverBase(QWidget* parentWindow);
        void selectFilenameAndSaveRole();

    protected:
        void saveFileError(const QString& filename, const QString& error_msg);
        void saveFileOK(const QString& filename);

        QWidget* mParentWindow;

        QString mSaveMessage;
        QString mFiletypeExtension;
        QString mFiletypeTemplate;
        QString mFixType;

    private:
        virtual void saveToFile(const QString& filename) = 0;
        QString guessFilenameStem() const;
};


/// Base for all profile-based remediation generators
template <QString* saveMessage, QString* filetypeExtension, QString* filetypeTemplate, QString* fixType>
class ProfileBasedRemediationSaver : public RemediationSaverBase<saveMessage, filetypeExtension, filetypeTemplate, fixType>
{
    public:
        ProfileBasedRemediationSaver(QWidget* parentWindow, ScanningSession* session);

    private:
        virtual void saveToFile(const QString& filename) override;
        const ScanningSession* mScanningSession;
};


/// Base for all result-based remediation generators
template <QString* saveMessage, QString* filetypeExtension, QString* filetypeTemplate, QString* fixType>
class ResultBasedRemediationSaver : public RemediationSaverBase<saveMessage, filetypeExtension, filetypeTemplate, fixType>
{
    public:
        ResultBasedRemediationSaver(QWidget* parentWindow, OscapScannerLocal* scanner);

    private:
        virtual void saveToFile(const QString& filename) override;
        OscapScannerLocal* mScanner;
};


static QString bashSaveMessage = QObject::tr("Save remediation role as a bash script");
static QString bashFiletypeExtension = "sh";
static QString bashFiletypeTemplate = QObject::tr("bash script (*.%1)");
static QString bashFixTemplate = QString("sh");
static QString bashFixType = QString("bash");

static QString ansibleSaveMessage = QObject::tr("Save remediation role as an ansible playbook");
static QString ansibleFiletypeExtension = "yml";
static QString ansibleFiletypeTemplate = QObject::tr("ansible playbook (*.%1)");
static QString ansibleFixType = QString("ansible");

static QString puppetSaveMessage = QObject::tr("Save remediation role as a puppet manifest");
static QString puppetFiletypeExtension = "pp";
static QString puppetFiletypeTemplate = QObject::tr("puppet manifest (*.%1)");
static QString puppetFixType = QString("puppet");


typedef ProfileBasedRemediationSaver<&bashSaveMessage, &bashFiletypeExtension, &bashFiletypeTemplate, &bashFixTemplate> BashProfileRemediationSaver;
typedef ProfileBasedRemediationSaver<&ansibleSaveMessage, &ansibleFiletypeExtension, &ansibleFiletypeTemplate, &ansibleFixType> AnsibleProfileRemediationSaver;
typedef ProfileBasedRemediationSaver<&puppetSaveMessage, &puppetFiletypeExtension, &puppetFiletypeTemplate, &puppetFixType> PuppetProfileRemediationSaver;

typedef ResultBasedRemediationSaver<&bashSaveMessage, &bashFiletypeExtension, &bashFiletypeTemplate, &bashFixType> BashResultRemediationSaver;
typedef ResultBasedRemediationSaver<&ansibleSaveMessage, &ansibleFiletypeExtension, &ansibleFiletypeTemplate, &ansibleFixType> AnsibleResultRemediationSaver;
typedef ResultBasedRemediationSaver<&puppetSaveMessage, &puppetFiletypeExtension, &puppetFiletypeTemplate, &puppetFixType> PuppetResultRemediationSaver;


#endif // SCAP_WORKBENCH_REMEDIATION_ROLE_SAVER_H_
